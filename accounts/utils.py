import boto3
from django.conf import settings
import logging

logger = logging.getLogger("django_mcq")


def get_ses_client():

    region = settings.AWS_REGION

    if settings.DJANGO_ENV != "DEVELOPMENT":

        try:
            s3_client = boto3.client('ses', region_name=region)
        except Exception as e:
            logger.error("Failed to login to S3 service without Secret key etc")
            logger.error(e)

        else:
            return s3_client

    try:
        s3_client = boto3.client(
            'ses',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    except Exception as e:
        logger.error("Failed to login to S3 service with all credentials")
        logger.error(e)
        return None

    else:
        return s3_client