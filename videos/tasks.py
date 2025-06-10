import boto3
import os
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django.conf import settings
from celery import shared_task

import logging

logger = logging.getLogger("django_mcq")


@shared_task
def delete_s3_file(video_id: int):

    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

    try:
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=f"videos/{video_id}.mp4")
    except (ClientError, Exception) as e:
        raise e
    else:
        return True