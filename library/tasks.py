import time
from celery import shared_task

@shared_task
def add(x: int, y: int):
    time.sleep(10)
    return x + y