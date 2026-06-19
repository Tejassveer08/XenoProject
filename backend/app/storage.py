# app/storage.py

import math


def chunk_storage_key(session_id: str, chunk_index: int) -> str:
    return f"uploads/{session_id}/chunks/{chunk_index:05d}"


def assembled_storage_key(session_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{session_id}/assembled/{safe_name}"


def output_storage_key(job_id: str, filename: str) -> str:
    return f"outputs/{job_id}/{filename}"


def generate_presigned_upload_url(bucket: str, key: str) -> str:
    # Dummy URL for demo deployment
    return f"/fake-upload/{key}"


def generate_presigned_download_url(bucket: str, key: str) -> str:
    # Dummy URL for demo deployment
    return f"/fake-download/{key}"


def compute_chunk_count(file_size: int, chunk_size: int) -> int:
    return max(1, math.ceil(file_size / chunk_size))


def compose_chunks(session_id: str, filename: str, chunk_count: int) -> str:
    """
    Demo version.
    Skip MinIO/S3 completely.
    Pretend assembly succeeded.
    """
    return assembled_storage_key(session_id, filename)
