from django.db import models

from django.contrib.auth.models import User

class LibChat(models.Model):
    title = models.CharField(max_length=128)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'title'], name='unique_lib_chat_title_per_user')
        ]


class LibMessage(models.Model):
    message_text = models.TextField()
    chat = models.ForeignKey(LibChat, on_delete=models.CASCADE)
    order_number = models.IntegerField(default=0)
    llm_response = models.BooleanField(default=False)

class LibDocuments(models.Model):
    name = models.CharField()
    saved_name = models.CharField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
