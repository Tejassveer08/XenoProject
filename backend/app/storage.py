import math

import boto3
from botocore.client import Config

from app.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def get_public_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def chunk_storage_key(session_id: str, chunk_index: int) -> str:
    return f"uploads/{session_id}/chunks/{chunk_index:05d}"


def assembled_storage_key(session_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{session_id}/assembled/{safe_name}"


def output_storage_key(job_id: str, filename: str) -> str:
    return f"outputs/{job_id}/{filename}"


def generate_presigned_upload_url(bucket: str, key: str) -> str:
    client = get_public_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )


def generate_presigned_download_url(bucket: str, key: str) -> str:
    client = get_public_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )


def compute_chunk_count(file_size: int, chunk_size: int) -> int:
    return max(1, math.ceil(file_size / chunk_size))


def compose_chunks(session_id: str, filename: str, chunk_count: int) -> str:
    client = get_s3_client()
    bucket = settings.s3_bucket_uploads
    dest_key = assembled_storage_key(session_id, filename)

    if chunk_count == 1:
        source_key = chunk_storage_key(session_id, 0)
        client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": source_key},
            Key=dest_key,
        )
    else:
        mpu = client.create_multipart_upload(Bucket=bucket, Key=dest_key)
        upload_id = mpu["UploadId"]
        try:
            uploaded_parts = []
            for i in range(chunk_count):
                source_key = chunk_storage_key(session_id, i)
                part = client.upload_part_copy(
                    Bucket=bucket,
                    Key=dest_key,
                    PartNumber=i + 1,
                    UploadId=upload_id,
                    CopySource={"Bucket": bucket, "Key": source_key},
                )
                uploaded_parts.append({"ETag": part["CopyPartResult"]["ETag"], "PartNumber": i + 1})
            client.complete_multipart_upload(
                Bucket=bucket,
                Key=dest_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": uploaded_parts},
            )
        except Exception:
            client.abort_multipart_upload(Bucket=bucket, Key=dest_key, UploadId=upload_id)
            raise

    return dest_key
