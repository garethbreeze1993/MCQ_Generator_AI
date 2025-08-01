import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from celery import shared_task

from accounts.utils import get_ses_client

import logging

logger = logging.getLogger("django_mcq")


@shared_task
def send_ses_email(to_email: list, subject, body_text, body_html=None, from_email=None):
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    ses_client = get_ses_client()

    if ses_client is None:
        logger.error("Unable to connect to SES service")
        raise Exception("No ses client found")

    message = {
        "Subject": {"Data": subject},
        "Body": {
            "Text": {"Data": body_text},
        }
    }

    if body_html:
        message["Body"]["Html"] = {"Data": body_html}

    try:
        response = ses_client.send_email(
            Source=from_email,
            Destination={"ToAddresses": to_email},
            Message=message
        )

    except ClientError as e:
        logger.error(e)
        raise e

    else:
        return response
