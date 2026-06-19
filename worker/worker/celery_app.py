from celery import Celery
from worker.config import settings

celery_app = Celery("xeno_worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=["worker.tasks"],
)
