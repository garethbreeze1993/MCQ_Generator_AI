from django.db import models
from django.contrib.auth.models import User
from videos.validators import validate_prompt_token_length

STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]



class Video(models.Model):
    title = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    celery_task_id = models.CharField(null=True, blank=True)
    prompt = models.CharField(validators=[validate_prompt_token_length])
    s_three_url = models.URLField()
