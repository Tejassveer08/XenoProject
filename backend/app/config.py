from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://xeno:xeno_secret@localhost:5432/xeno_validation"
    database_url_sync: str = "postgresql://xeno:xeno_secret@localhost:5432/xeno_validation"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_bucket_uploads: str = "xeno-uploads"
    s3_bucket_outputs: str = "xeno-outputs"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000,http://localhost:8000,*"
    max_file_size_bytes: int = 10 * 1024 * 1024 * 1024  # 10 GB
    default_chunk_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    presigned_url_expiry_seconds: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()
