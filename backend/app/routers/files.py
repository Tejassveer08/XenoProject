from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import OutputFile, User, ValidationJob
from app.schemas import OutputFileResponse
from app.storage import generate_presigned_download_url

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}", response_model=OutputFileResponse)
async def get_file_info(
    file_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(OutputFile, ValidationJob)
        .join(ValidationJob, OutputFile.validation_job_id == ValidationJob.id)
        .where(OutputFile.id == file_id, ValidationJob.user_id == current_user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    output_file, _ = row
    return OutputFileResponse(
        id=output_file.id,
        file_type=output_file.file_type,
        filename=output_file.filename,
        file_size=output_file.file_size,
        chunk_index=output_file.chunk_index,
        row_count=output_file.row_count,
        is_valid_only=output_file.is_valid_only,
        download_url=generate_presigned_download_url(settings.s3_bucket_outputs, output_file.storage_key),
    )
