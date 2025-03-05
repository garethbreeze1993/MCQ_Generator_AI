from django.db import models

from django.contrib.auth.models import User

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT / user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.id, filename)

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_file = models.FileField(upload_to=user_directory_path)
    datetime_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class LibDocumentEmbeddings(models.Model):
    document = models.ForeignKey(LibDocuments, on_delete=models.CASCADE)
    start_id = models.IntegerField()
    end_id = models.IntegerField()


