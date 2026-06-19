from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.celery_app import celery_app
from app.database import get_db
from app.models import JobStatus, UploadSession, UploadStatus, User, ValidationJob
from app.schemas import ValidationJobCreate, ValidationJobListItem, ValidationJobResponse
from app.storage import generate_presigned_download_url
from app.config import settings

router = APIRouter(prefix="/validation-jobs", tags=["validation-jobs"])


def _job_response(job: ValidationJob) -> ValidationJobResponse:
    output_files = []
    for f in job.output_files or []:
        output_files.append(
            {
                "id": f.id,
                "file_type": f.file_type,
                "filename": f.filename,
                "file_size": f.file_size,
                "chunk_index": f.chunk_index,
                "row_count": f.row_count,
                "is_valid_only": f.is_valid_only,
                "download_url": generate_presigned_download_url(settings.s3_bucket_outputs, f.storage_key),
            }
        )
    return ValidationJobResponse(
        id=job.id,
        upload_session_id=job.upload_session_id,
        dataset_type=job.dataset_type,
        rule_set=job.rule_set,
        options=job.options or {},
        status=job.status.value,
        progress=job.progress,
        error_message=job.error_message,
        stats=job.stats,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        output_files=output_files,
    )


@router.post("", response_model=ValidationJobResponse, status_code=status.HTTP_201_CREATED)
async def create_validation_job(
    payload: ValidationJobCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.id == payload.upload_session_id,
            UploadSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session.status != UploadStatus.COMPLETED or not session.storage_key:
        raise HTTPException(status_code=400, detail="Upload session is not complete")

    job = ValidationJob(
        user_id=current_user.id,
        upload_session_id=session.id,
        dataset_type=payload.dataset_type,
        rule_set=payload.rule_set,
        options=payload.options,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    celery_app.send_task("worker.tasks.process_validation_job", args=[job.id], queue="validation")

    return ValidationJobResponse(
        id=job.id,
        upload_session_id=job.upload_session_id,
        dataset_type=job.dataset_type,
        rule_set=job.rule_set,
        options=job.options or {},
        status=job.status.value,
        progress=job.progress,
        error_message=job.error_message,
        stats=job.stats,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        output_files=[],
    )


@router.get("", response_model=list[ValidationJobListItem])
async def list_validation_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ValidationJob)
        .where(ValidationJob.user_id == current_user.id)
        .order_by(ValidationJob.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()
    return [
        ValidationJobListItem(
            id=j.id,
            dataset_type=j.dataset_type,
            rule_set=j.rule_set,
            status=j.status.value,
            progress=j.progress,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await _get_user_job(db, job_id, current_user.id)
    return _job_response(job)


async def _get_user_job(db: AsyncSession, job_id: str, user_id: str) -> ValidationJob:
    result = await db.execute(
        select(ValidationJob)
        .options(selectinload(ValidationJob.output_files))
        .where(ValidationJob.id == job_id, ValidationJob.user_id == user_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Validation job not found")
    return job
