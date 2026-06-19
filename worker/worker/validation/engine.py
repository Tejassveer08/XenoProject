from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import phonenumbers
import polars as pl
from dateutil import parser as date_parser

from worker.config import settings


@dataclass
class ValidationResult:
    cleaned_chunks: list[str] = field(default_factory=list)
    chunk_row_counts: list[int] = field(default_factory=list)
    error_report_path: str | None = None
    error_count: int = 0
    valid_only: bool = False
    stats: dict[str, Any] = field(default_factory=dict)


class ValidationEngine:
    def __init__(
        self,
        dataset_rules: dict,
        global_rules: dict | None = None,
        options: dict | None = None,
    ):
        self.dataset_rules = dataset_rules
        self.global_rules = global_rules or {}
        self.options = options or {}
        self.valid_only = self.options.get("valid_only", False)
        self.chunk_rows = self.options.get("chunk_rows", settings.output_chunk_rows)
        self.fields = {f["name"]: f for f in dataset_rules.get("fields", [])}
        self.cross_field = dataset_rules.get("cross_field_checks", [])
        self.country_phone_rules = (global_rules or {}).get("country_phone_rules", {})

    def process(self, csv_path: str, progress_callback: Callable[[float], None] | None = None) -> ValidationResult:
        lf = pl.scan_csv(csv_path, infer_schema_length=10000, ignore_errors=True)
        df = lf.collect(streaming=True)
        total_rows = df.height

        if progress_callback:
            progress_callback(0.1)

        errors: list[dict] = []
        row_valid = [True] * total_rows
        error_summaries: list[str] = [""] * total_rows

        for field_name, field_def in self.fields.items():
            if field_name not in df.columns:
                if field_def.get("required"):
                    for i in range(total_rows):
                        self._add_error(errors, row_valid, error_summaries, i, field_name, "REQUIRED", f"Missing column: {field_name}")
                continue

            col = df[field_name]
            for i in range(total_rows):
                val = col[i]
                field_errors = self._validate_field(val, field_def, df, i)
                for err in field_errors:
                    self._add_error(errors, row_valid, error_summaries, i, field_name, err["code"], err["message"])

        for check in self.cross_field:
            self._apply_cross_field_check(df, check, errors, row_valid, error_summaries)

        if progress_callback:
            progress_callback(0.6)

        df = df.with_columns(
            pl.Series("is_valid", row_valid),
            pl.Series("error_summary", error_summaries),
        )

        normalized_cols = []
        for field_name, field_def in self.fields.items():
            if field_name in df.columns and field_def.get("type") in ("phone",):
                normalized_cols.append(
                    pl.col(field_name).map_elements(
                        lambda v, fd=field_def: self._normalize_phone(v, fd),
                        return_dtype=pl.Utf8,
                    ).alias(f"{field_name}_normalized")
                )
            elif field_name in df.columns and field_def.get("type") in ("date", "datetime"):
                normalized_cols.append(
                    pl.col(field_name).map_elements(
                        lambda v, fd=field_def: self._normalize_date(v, fd),
                        return_dtype=pl.Utf8,
                    ).alias(f"{field_name}_normalized")
                )

        if normalized_cols:
            df = df.with_columns(normalized_cols)

        output_df = df.filter(pl.col("is_valid")) if self.valid_only else df

        import tempfile
        import os

        cleaned_chunks: list[str] = []
        chunk_counts: list[int] = []

        if output_df.height == 0:
            fd, path = tempfile.mkstemp(suffix=".csv")
            os.close(fd)
            pl.DataFrame().write_csv(path)
            cleaned_chunks.append(path)
            chunk_counts.append(0)
        else:
            for start in range(0, output_df.height, self.chunk_rows):
                chunk = output_df.slice(start, self.chunk_rows)
                fd, path = tempfile.mkstemp(suffix=".csv")
                os.close(fd)
                chunk.write_csv(path)
                cleaned_chunks.append(path)
                chunk_counts.append(chunk.height)

        error_path = None
        if errors:
            fd, error_path = tempfile.mkstemp(suffix=".csv")
            os.close(fd)
            pl.DataFrame(errors).write_csv(error_path)

        valid_count = sum(row_valid)
        stats = {
            "total_rows": total_rows,
            "valid_rows": valid_count,
            "invalid_rows": total_rows - valid_count,
            "valid_percentage": round(100 * valid_count / total_rows, 2) if total_rows else 0,
            "errors_by_code": self._count_by_code(errors),
            "output_chunks": len(cleaned_chunks),
        }

        if progress_callback:
            progress_callback(1.0)

        return ValidationResult(
            cleaned_chunks=cleaned_chunks,
            chunk_row_counts=chunk_counts,
            error_report_path=error_path,
            error_count=len(errors),
            valid_only=self.valid_only,
            stats=stats,
        )

    def _validate_field(self, value: Any, field_def: dict, df: pl.DataFrame, row_idx: int) -> list[dict]:
        errors = []
        name = field_def["name"]
        ftype = field_def.get("type", "string")
        required = field_def.get("required", False)

        if value is None or (isinstance(value, str) and value.strip() == ""):
            if required:
                errors.append({"code": "REQUIRED", "message": f"{name} is required"})
            return errors

        str_val = str(value).strip()
        constraints = field_def.get("constraints", {})

        if ftype == "integer":
            try:
                int_val = int(float(str_val))
                if "min" in constraints and int_val < constraints["min"]:
                    errors.append({"code": "RANGE", "message": f"{name} below minimum {constraints['min']}"})
                if "max" in constraints and int_val > constraints["max"]:
                    errors.append({"code": "RANGE", "message": f"{name} above maximum {constraints['max']}"})
            except ValueError:
                errors.append({"code": "TYPE", "message": f"{name} must be an integer"})

        elif ftype == "float":
            try:
                float_val = float(str_val)
                if "min" in constraints and float_val < constraints["min"]:
                    errors.append({"code": "RANGE", "message": f"{name} below minimum {constraints['min']}"})
                if "max" in constraints and float_val > constraints["max"]:
                    errors.append({"code": "RANGE", "message": f"{name} above maximum {constraints['max']}"})
            except ValueError:
                errors.append({"code": "TYPE", "message": f"{name} must be a number"})

        elif ftype == "enum":
            allowed = constraints.get("allowed", [])
            if str_val not in allowed:
                errors.append({"code": "ENUM", "message": f"{name} must be one of {allowed}"})

        elif ftype == "phone":
            region = self._get_phone_region(df, row_idx, field_def)
            phone_errors = validate_phone(str_val, region, self.country_phone_rules.get(region, {}))
            errors.extend(phone_errors)

        elif ftype in ("date", "datetime"):
            date_errors = validate_date(str_val, field_def)
            errors.extend(date_errors)

        elif ftype == "string":
            if "regex" in constraints:
                if not re.match(constraints["regex"], str_val):
                    errors.append({"code": "REGEX", "message": f"{name} does not match required pattern"})
            if "min_length" in constraints and len(str_val) < constraints["min_length"]:
                errors.append({"code": "LENGTH", "message": f"{name} too short"})
            if "max_length" in constraints and len(str_val) > constraints["max_length"]:
                errors.append({"code": "LENGTH", "message": f"{name} too long"})

        if "unique" in constraints and constraints["unique"]:
            col_name = field_def["name"]
            if col_name in df.columns:
                matches = (df[col_name].cast(pl.Utf8) == str_val).sum()
                if matches > 1:
                    errors.append({"code": "UNIQUE", "message": f"{name} must be unique"})

        return errors

    def _get_phone_region(self, df: pl.DataFrame, row_idx: int, field_def: dict) -> str:
        region_col = field_def.get("region_column") or self.global_rules.get("default_country_column")
        default = field_def.get("default_region") or self.global_rules.get("default_country", "US")
        if region_col and region_col in df.columns:
            val = df[region_col][row_idx]
            if val is not None and str(val).strip():
                return str(val).strip().upper()[:2]
        return default

    def _apply_cross_field_check(self, df, check, errors, row_valid, error_summaries):
        check_type = check.get("type")
        if check_type == "date_order":
            left, right = check["left"], check["right"]
            if left not in df.columns or right not in df.columns:
                return
            for i in range(df.height):
                lv, rv = df[left][i], df[right][i]
                if lv is None or rv is None or str(lv).strip() == "" or str(rv).strip() == "":
                    continue
                try:
                    ld = date_parser.parse(str(lv))
                    rd = date_parser.parse(str(rv))
                    if ld > rd:
                        msg = check.get("message", f"{left} must be before {right}")
                        self._add_error(errors, row_valid, error_summaries, i, left, "DATE_ORDER", msg)
                except (ValueError, TypeError):
                    pass

        elif check_type == "future_tolerance":
            field = check["field"]
            days = check.get("max_future_days", 0)
            if field not in df.columns:
                return
            from datetime import datetime, timedelta

            limit = datetime.utcnow() + timedelta(days=days)
            for i in range(df.height):
                val = df[field][i]
                if val is None or str(val).strip() == "":
                    continue
                try:
                    dt = date_parser.parse(str(val))
                    if dt.replace(tzinfo=None) > limit:
                        self._add_error(errors, row_valid, error_summaries, i, field, "FUTURE_DATE", f"{field} is too far in the future")
                except (ValueError, TypeError):
                    pass

    def _normalize_phone(self, value: Any, field_def: dict) -> str:
        if value is None or str(value).strip() == "":
            return ""
        region = field_def.get("default_region", self.global_rules.get("default_country", "US"))
        try:
            parsed = phonenumbers.parse(str(value), region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass
        return str(value)

    def _normalize_date(self, value: Any, field_def: dict) -> str:
        if value is None or str(value).strip() == "":
            return ""
        formats = field_def.get("constraints", {}).get("formats", [])
        try:
            if formats:
                from datetime import datetime

                for fmt in formats:
                    try:
                        return datetime.strptime(str(value).strip(), fmt).isoformat()
                    except ValueError:
                        continue
            return date_parser.parse(str(value)).isoformat()
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _add_error(errors, row_valid, error_summaries, row_idx, field_name, code, message):
        row_valid[row_idx] = False
        if error_summaries[row_idx]:
            error_summaries[row_idx] += "; "
        error_summaries[row_idx] += message
        errors.append(
            {
                "row_number": row_idx + 2,
                "field_name": field_name,
                "error_code": code,
                "error_message": message,
            }
        )

    @staticmethod
    def _count_by_code(errors: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in errors:
            code = e["error_code"]
            counts[code] = counts.get(code, 0) + 1
        return counts


def validate_phone(value: str, region: str, country_rules: dict | None = None) -> list[dict]:
    errors = []
    country_rules = country_rules or {}
    try:
        parsed = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        errors.append({"code": "PHONE_PARSE", "message": f"Cannot parse phone number for region {region}"})
        return errors

    if not phonenumbers.is_possible_number(parsed):
        errors.append({"code": "PHONE_POSSIBLE", "message": "Phone number length/format is not possible"})
    if not phonenumbers.is_valid_number(parsed):
        errors.append({"code": "PHONE_INVALID", "message": "Phone number is not valid for the region"})

    digits = re.sub(r"\D", "", value)
    expected_len = country_rules.get("digits")
    if expected_len and len(digits) != expected_len:
        errors.append({"code": "PHONE_LENGTH", "message": f"Expected {expected_len} digits for {region}"})

    prefix = country_rules.get("prefix")
    if prefix and not digits.startswith(prefix.replace("+", "")):
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        if not national.replace(" ", "").startswith(prefix.replace("+", "")):
            pass

    return errors


def validate_date(value: str, field_def: dict) -> list[dict]:
    errors = []
    constraints = field_def.get("constraints", {})
    formats = constraints.get("formats", ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"])

    parsed = None
    for fmt in formats:
        try:
            from datetime import datetime

            parsed = datetime.strptime(value.strip(), fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError):
            errors.append({"code": "DATE_FORMAT", "message": f"Unrecognized date format: {value}"})
            return errors

    if constraints.get("not_future"):
        from datetime import datetime

        if parsed.replace(tzinfo=None) > datetime.utcnow():
            errors.append({"code": "FUTURE_DATE", "message": "Date cannot be in the future"})

    return errors
