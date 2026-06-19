from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    api_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadSessionCreate(BaseModel):
    filename: str
    file_size: int = Field(gt=0)
    content_type: str = "text/csv"
    chunk_size: int | None = None


class ChunkUploadInfo(BaseModel):
    chunk_index: int
    upload_url: str


class UploadSessionResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    chunk_size: int
    chunk_count: int
    uploaded_chunks: list[int]
    status: str
    storage_key: str | None
    created_at: datetime
    chunk_urls: list[ChunkUploadInfo] | None = None

    model_config = {"from_attributes": True}


class ChunkCompleteRequest(BaseModel):
    chunk_index: int
    etag: str | None = None


class UploadCompleteRequest(BaseModel):
    chunks: list[ChunkCompleteRequest] | None = None


class ValidationJobCreate(BaseModel):
    upload_session_id: str
    dataset_type: str = "orders"
    rule_set: str = "default"
    options: dict[str, Any] = Field(default_factory=dict)


class OutputFileResponse(BaseModel):
    id: str
    file_type: str
    filename: str
    file_size: int
    chunk_index: int | None
    row_count: int | None
    is_valid_only: bool
    download_url: str | None = None

    model_config = {"from_attributes": True}


class ValidationJobResponse(BaseModel):
    id: str
    upload_session_id: str
    dataset_type: str
    rule_set: str
    options: dict[str, Any]
    status: str
    progress: float
    error_message: str | None
    stats: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    output_files: list[OutputFileResponse] = []

    model_config = {"from_attributes": True}


class ValidationJobListItem(BaseModel):
    id: str
    dataset_type: str
    rule_set: str
    status: str
    progress: float
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
