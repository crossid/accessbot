from celery import Celery

from app.settings import settings

celery_app = Celery(
    "tasks", broker="sqla+" + settings.DB_URI, backend="db+" + settings.DB_URI
)

celery_app.autodiscover_tasks(["app.data_fetching.factory"])
