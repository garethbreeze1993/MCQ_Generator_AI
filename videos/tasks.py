import boto3
import os
import requests
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django.conf import settings
from celery import shared_task

from videos.utils import get_s3_client

import logging

from videos.models import Video

logger = logging.getLogger("django_mcq")


@shared_task
def delete_s3_file(video_id: int):

    s3 = get_s3_client()

    if s3 is None:
        raise Exception("S3 Client not initialized")

    try:
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=f"videos/{video_id}.mp4")
    except (ClientError, Exception) as e:
        raise e
    else:
        return True

@shared_task(bind=True)
def send_request_to_text_to_vid_api(self, video_id: int, prompt: str):
    status_msg = "uploaded"
    try:
        # Step 1: Submit job to FastAPI
        response = requests.post(
            f"{settings.VIDEOAPI_BASE_URL}/generate",
            json={
                "prompt": prompt,
                "video_id": video_id,
                "celery_task_id": self.request.id
            },
            timeout=30
        )
        response.raise_for_status()

        status_msg = "processing"

    except requests.exceptions.RequestException as e:
        status_msg = "error"
        raise e

    except Exception as e:
        status_msg = "error"
        raise e

    else:
        return "Successfully sent to FASTAPI"

    finally:
        video = Video.objects.get(pk=video_id)
        video.status = status_msg
        video.save()


@shared_task
def send_test_request():

    try:
        # Step 1: Submit job to FastAPI
        response = requests.get(
            f"{settings.VIDEOAPI_BASE_URL}/test"
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise e

    except Exception as e:
        raise e

    else:
        return "Successfully sent to FASTAPI TEST"


