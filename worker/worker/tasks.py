import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worker.config import settings
from worker.validation.engine import ValidationEngine

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _load_models():
    from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
    import enum

    class Base(DeclarativeBase):
        pass

    class JobStatus(str, enum.Enum):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"

    class UploadSession(Base):
        __tablename__ = "upload_sessions"
        id: Mapped[str] = mapped_column(String(36), primary_key=True)
        storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    class ValidationJob(Base):
        __tablename__ = "validation_jobs"
        id: Mapped[str] = mapped_column(String(36), primary_key=True)
        upload_session_id: Mapped[str] = mapped_column(String(36))
        dataset_type: Mapped[str] = mapped_column(String(64))
        rule_set: Mapped[str] = mapped_column(String(64))
        options: Mapped[dict] = mapped_column(JSON, default=dict)
        status: Mapped[JobStatus] = mapped_column(Enum(JobStatus))
        progress: Mapped[float] = mapped_column(Float, default=0.0)
        error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
        stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
        started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
        completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
        output_files: Mapped[list] = relationship("OutputFile", back_populates="validation_job")

    class OutputFile(Base):
        __tablename__ = "output_files"
        id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        validation_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("validation_jobs.id"))
        file_type: Mapped[str] = mapped_column(String(64))
        filename: Mapped[str] = mapped_column(String(512))
        storage_key: Mapped[str] = mapped_column(String(1024))
        file_size: Mapped[int] = mapped_column(BigInteger, default=0)
        chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
        row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
        is_valid_only: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
        validation_job: Mapped["ValidationJob"] = relationship(back_populates="output_files")

    return JobStatus, OutputFile, UploadSession, ValidationJob


@shared_task(name="worker.tasks.process_validation_job")
def process_validation_job(job_id: str):
    JobStatus, OutputFile, UploadSession, ValidationJob = _load_models()

    db: Session = SessionLocal()
    s3 = get_s3_client()
    tmp_path = None

    try:
        job = db.get(ValidationJob, job_id)
        if not job:
            return {"error": "Job not found"}

        if job.status in (JobStatus.SUCCEEDED, JobStatus.RUNNING):
            return {"status": job.status.value}

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.progress = 5.0
        db.commit()

        session = db.get(UploadSession, job.upload_session_id)
        if not session or not session.storage_key:
            job.status = JobStatus.FAILED
            job.error_message = "Upload file not found"
            db.commit()
            return

        rules_path = Path(settings.rules_dir) / f"{job.rule_set}.json"
        if not rules_path.exists():
            rules_path = Path(__file__).resolve().parents[2] / "shared" / "rules" / f"{job.rule_set}.json"

        with open(rules_path, encoding="utf-8") as f:
            rules = json.load(f)

        dataset_rules = rules.get("datasets", {}).get(job.dataset_type)
        if not dataset_rules:
            job.status = JobStatus.FAILED
            job.error_message = f"No rules for dataset type: {job.dataset_type}"
            db.commit()
            return

        fd, tmp_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        s3.download_file(settings.s3_bucket_uploads, session.storage_key, tmp_path)

        job.progress = 20.0
        db.commit()

        validator = ValidationEngine(
            dataset_rules=dataset_rules,
            global_rules=rules.get("global", {}),
            options=job.options or {},
        )
        result = validator.process(tmp_path, progress_callback=lambda p: _update_progress(db, job, 20 + p * 0.7))

        job.progress = 95.0
        db.commit()

        output_prefix = f"outputs/{job.id}"
        chunk_files = _upload_outputs(s3, db, job, OutputFile, result, output_prefix)

        job.status = JobStatus.SUCCEEDED
        job.progress = 100.0
        job.completed_at = datetime.utcnow()
        job.stats = result.stats
        db.commit()

        return {"status": "SUCCEEDED", "output_files": len(chunk_files), "stats": result.stats}

    except Exception as exc:
        db.rollback()
        job = db.get(ValidationJob, job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        db.close()


def _update_progress(db: Session, job, progress: float):
    job.progress = min(progress, 90.0)
    db.commit()


def _upload_outputs(s3, db, job, OutputFile, result, output_prefix):
    files_created = []
    bucket = settings.s3_bucket_outputs

    for i, chunk_path in enumerate(result.cleaned_chunks):
        filename = f"cleaned_part_{i:04d}.csv"
        key = f"{output_prefix}/{filename}"
        s3.upload_file(chunk_path, bucket, key)
        size = os.path.getsize(chunk_path)
        of = OutputFile(
            validation_job_id=job.id,
            file_type="cleaned_chunk",
            filename=filename,
            storage_key=key,
            file_size=size,
            chunk_index=i,
            row_count=result.chunk_row_counts[i] if i < len(result.chunk_row_counts) else None,
            is_valid_only=result.valid_only,
        )
        db.add(of)
        files_created.append(of)
        os.unlink(chunk_path)

    if result.error_report_path:
        err_filename = "errors.csv"
        err_key = f"{output_prefix}/{err_filename}"
        s3.upload_file(result.error_report_path, bucket, err_key)
        size = os.path.getsize(result.error_report_path)
        of = OutputFile(
            validation_job_id=job.id,
            file_type="errors",
            filename=err_filename,
            storage_key=err_key,
            file_size=size,
            row_count=result.error_count,
            is_valid_only=False,
        )
        db.add(of)
        files_created.append(of)
        os.unlink(result.error_report_path)

    db.commit()
    return files_created
