import math
import os
import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BUCKET = "xeno-uploads"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


# ==================================================
# Key Helpers
# ==================================================

def chunk_storage_key(session_id: str, chunk_index: int) -> str:
    return f"uploads/{session_id}/chunks/{chunk_index:05d}"


def assembled_storage_key(session_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{session_id}/assembled/{safe_name}"


def output_storage_key(job_id: str, filename: str) -> str:
    return f"outputs/{job_id}/{filename}"


def compute_chunk_count(file_size: int, chunk_size: int) -> int:
    return max(1, math.ceil(file_size / chunk_size))


# ==================================================
# Upload / Download
# ==================================================

def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes directly to Supabase Storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}"
    headers = {**HEADERS, "Content-Type": content_type}
    response = httpx.put(url, content=data, headers=headers)
    response.raise_for_status()


def download_bytes(key: str) -> bytes:
    """Download raw bytes from Supabase Storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{key}"
    response = httpx.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.content


def generate_presigned_download_url(bucket: str, key: str) -> str:
    """Generate a signed download URL valid for 1 hour."""
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET}/{key}"
    response = httpx.post(url, json={"expiresIn": 3600}, headers=HEADERS)
    response.raise_for_status()
    signed = response.json().get("signedURL", "")
    return f"{SUPABASE_URL}/storage/v1{signed}"


# ==================================================
# Chunk Assembly
# ==================================================

def compose_chunks(session_id: str, filename: str, chunk_count: int) -> str:
    """Download all chunks and reassemble into a single file in Supabase Storage."""
    assembled_data = b""

    for i in range(chunk_count):
        key = chunk_storage_key(session_id, i)
        assembled_data += download_bytes(key)

    assembled_key = assembled_storage_key(session_id, filename)
    upload_bytes(assembled_key, assembled_data, content_type="text/csv")

    return assembled_key
