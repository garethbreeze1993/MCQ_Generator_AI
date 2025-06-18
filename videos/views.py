import boto3
from botocore.exceptions import ClientError

from io import BytesIO

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.http import Http404, FileResponse

import logging

from videos.forms import VideoForm
from videos.tasks import delete_s3_file, send_request_to_text_to_vid_api, send_test_request

from django.contrib import messages

from videos.models import Video

logger = logging.getLogger("django_mcq")


class VideoListView(LoginRequiredMixin, ListView):
    model = Video
    paginate_by = 10  # if pagination is desired
    template_name = 'videos/video_index.html'  # Specify your template name
    context_object_name = 'videos'  # The variable to use in the template

    def get_queryset(self):
        # Filter quizzes by the current logged-in user
        return Video.objects.filter(user=self.request.user)

class VideoDetailView(LoginRequiredMixin, DetailView):
    model = Video
    template_name = "videos/video_detail.html"
    context_object_name = "video"

    def get_queryset(self):
        # Ensure users can only access their own documents
        return Video.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs.get("pk"))

@login_required(login_url='login')
def upload_video(request):
    form = None

    if request.method == "POST":

        form = VideoForm(request.POST)

        if form.is_valid():
            video = form.save(commit=False)  # Don't save yet
            video.user = request.user  # Assign the logged-in user
            region = settings.AWS_REGION
            s3_bucket = settings.S3_BUCKET_NAME
            s3_key = f"videos/{video.pk}.mp4"
            s3_url = f"https://{s3_bucket}.s3.{region}.amazonaws.com/{s3_key}"
            video.s_three_url = s3_url
            video.celery_task_id = None

            try:
                video.save()
            except Exception as e:
                logger.error(e)
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, "videos/upload_video.html", {"form": form})

            send_request_to_text_to_vid_api.delay_on_commit(video_id=video.pk, prompt=video.prompt)

            messages.success(request, "Data saved successfully!")
            return redirect("video_index")  # Redirect after saving

        else:
            logger.error(form.errors)
            return render(request, "videos/upload_video.html", {"form": form})

    else:
        # Request method is GET
        form = VideoForm()

        return render(request, "videos/upload_video.html", {"form": form})

class VideoDeleteView(LoginRequiredMixin, DeleteView):
    # specify the model you want to use
    model = Video
    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_url = reverse_lazy("video_index")
    template_name = "videos/confirm_vid_delete.html"

    def get_queryset(self):
        """
        Limit the queryset to quizzes owned by the logged-in user.
        """
        return Video.objects.filter(user=self.request.user)

    def handle_no_permission(self):
        """
        Handle unauthorized access attempts.
        """
        raise Http404("You do not have permission to delete this quiz.")

    def form_valid(self, form):

        instance = self.get_object()

        delete_s3_file.delay_on_commit(video_id=instance.pk)

        # Proceed with the standard delete operation
        return super().form_valid(form)

@login_required
def download_video(request, pk):

    # Get the file object
    video = get_object_or_404(Video, pk=pk, user=request.user)

    try:

        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

        s3_object = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=f"videos/{video.pk}.mp4")

        file_stream = BytesIO(s3_object['Body'].read())

        # Return the file response
        response = FileResponse(file_stream, as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{video.pk}.mp4"'


    except ClientError as client_error:
        if client_error.response['Error']['Code'] == 'NoSuchKey':
            logger.error(client_error)
            messages.error(request, "File not found in S3")
        else:
            logger.error(client_error)
            messages.error(request, "An error occurred")

        return redirect("video_detail", pk=video.pk)

    except Exception as e:
        logger.error(e)
        messages.error(request, "An error occurred")
        return redirect("video_detail", pk=video.pk)

    else:
        return response

@login_required
def test_video(request):
    send_test_request.delay()
    return redirect("video_index")
