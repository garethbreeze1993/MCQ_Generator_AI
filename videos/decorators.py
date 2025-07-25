import requests
from videos.models import Video
from django.conf import settings
from django.db import transaction

from functools import wraps

import logging

logger = logging.getLogger("django_mcq")

def is_fastapi_online():
    try:
        response = requests.get(f"{settings.VIDEOAPI_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def mark_video_for_retry_if_fastapi_down(task_func):
    @wraps(task_func)
    def wrapper(self, video_id, *args, **kwargs):
        if not is_fastapi_online():
            # Update video status to "retry"
            with transaction.atomic():
                try:
                    video = Video.objects.select_for_update().get(id=video_id)
                    video.status = "retry"
                    video.save()
                except Video.DoesNotExist:
                    logger.error(f"Video doesn not exist with id === {video_id}")
                    pass
            return  # skip running the task
        return task_func(self, video_id, *args, **kwargs)
    return wrapper
