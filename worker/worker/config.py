from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://xeno:xeno_secret@localhost:5432/xeno_validation"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_bucket_uploads: str = "xeno-uploads"
    s3_bucket_outputs: str = "xeno-outputs"
    output_chunk_rows: int = 100_000
    rules_dir: str = "/app/shared/rules"

    class Config:
        env_file = ".env"


settings = Settings()
