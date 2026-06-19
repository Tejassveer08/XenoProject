from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import UploadSession, UploadStatus, User
from app.schemas import (
    ChunkUploadInfo,
    UploadCompleteRequest,
    UploadSessionCreate,
    UploadSessionResponse,
)
from app.storage import (
    chunk_storage_key,
    compose_chunks,
    compute_chunk_count,
    generate_presigned_upload_url,
)

router = APIRouter(prefix="/upload-sessions", tags=["upload-sessions"])


def _session_response(session: UploadSession, include_urls: bool = False) -> UploadSessionResponse:
    chunk_urls = None
    if include_urls:
        chunk_urls = [
            ChunkUploadInfo(
                chunk_index=i,
                upload_url=generate_presigned_upload_url(
                    settings.s3_bucket_uploads,
                    chunk_storage_key(session.id, i),
                ),
            )
            for i in range(session.chunk_count)
        ]
    return UploadSessionResponse(
        id=session.id,
        filename=session.filename,
        file_size=session.file_size,
        chunk_size=session.chunk_size,
        chunk_count=session.chunk_count,
        uploaded_chunks=session.uploaded_chunks or [],
        status=session.status.value,
        storage_key=session.storage_key,
        created_at=session.created_at,
        chunk_urls=chunk_urls,
    )


@router.post("", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_session(
    payload: UploadSessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if payload.file_size > settings.max_file_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed size")

    chunk_size = payload.chunk_size or settings.default_chunk_size_bytes
    chunk_count = compute_chunk_count(payload.file_size, chunk_size)

    session = UploadSession(
        user_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        file_size=payload.file_size,
        chunk_size=chunk_size,
        chunk_count=chunk_count,
        uploaded_chunks=[],
        status=UploadStatus.CREATED,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    session.status = UploadStatus.UPLOADING
    await db.commit()
    return _session_response(session, include_urls=True)


@router.get("/{session_id}", response_model=UploadSessionResponse)
async def get_upload_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_user_session(db, session_id, current_user.id)
    return _session_response(session, include_urls=session.status == UploadStatus.UPLOADING)


@router.post("/{session_id}/chunks/{chunk_index}/complete")
async def mark_chunk_complete(
    session_id: str,
    chunk_index: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_user_session(db, session_id, current_user.id)
    if session.status not in (UploadStatus.CREATED, UploadStatus.UPLOADING):
        raise HTTPException(status_code=400, detail="Upload session is not accepting chunks")
    if chunk_index < 0 or chunk_index >= session.chunk_count:
        raise HTTPException(status_code=400, detail="Invalid chunk index")

    uploaded = list(session.uploaded_chunks or [])
    if chunk_index not in uploaded:
        uploaded.append(chunk_index)
        uploaded.sort()
        session.uploaded_chunks = uploaded
        await db.commit()
    return {"uploaded_chunks": session.uploaded_chunks, "complete": len(uploaded) == session.chunk_count}


@router.post("/{session_id}/complete", response_model=UploadSessionResponse)
async def complete_upload(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: UploadCompleteRequest | None = None,
):
    session = await _get_user_session(db, session_id, current_user.id)
    if session.status == UploadStatus.COMPLETED:
        return _session_response(session)

    uploaded = set(session.uploaded_chunks or [])
    if body and body.chunks:
        uploaded.update(c.chunk_index for c in body.chunks)

    expected = set(range(session.chunk_count))
    if uploaded != expected:
        missing = sorted(expected - uploaded)
        raise HTTPException(
            status_code=400,
            detail=f"Not all chunks uploaded. Missing: {missing}",
        )

    try:
        storage_key = compose_chunks(session.id, session.filename, session.chunk_count)
        session.storage_key = storage_key
        session.status = UploadStatus.COMPLETED
        from datetime import datetime

        session.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(session)
    except Exception as exc:
        session.status = UploadStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to assemble upload: {exc}") from exc

    return _session_response(session)


async def _get_user_session(db: AsyncSession, session_id: str, user_id: str) -> UploadSession:
    result = await db.execute(
        select(UploadSession).where(UploadSession.id == session_id, UploadSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    return session
