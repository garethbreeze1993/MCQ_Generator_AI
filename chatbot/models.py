from django.db import models

from django.contrib.auth.models import User

class Chat(models.Model):
    title = models.CharField(max_length=128)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'title'], name='unique_chat_title_per_user')
        ]


class Message(models.Model):
    message_text = models.TextField()
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    order_number = models.IntegerField(default=0)
    llm_response = models.BooleanField(default=False)