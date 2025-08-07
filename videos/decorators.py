import requests
from videos.models import Video
from django.conf import settings
from django.db import transaction

from accounts.tasks import send_ses_email
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
                else:
                    subject, message = prepare_message_api_down(video)
                    send_ses_email.delay(to_email=[settings.CONTACT_FORM_RECIPIENT],
                                         from_email=settings.DEFAULT_FROM_EMAIL,
                                         subject=subject,
                                         body_text=message)

            return  # skip running the task
        return task_func(self, video_id, *args, **kwargs)
    return wrapper


def prepare_message_api_down(video: Video):
    subject = "API is DOWN Please Start"

    message = f"""
        Video_title === {video.title}
        \n\n
        Video_user === {video.user}
        \n\n
        Video_status === {video.status}
        \n\n
        Video_prompt === {video.prompt}
        \n\n
        Video_id === {video.id}
    """
    return subject, message