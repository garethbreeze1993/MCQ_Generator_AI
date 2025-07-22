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
from django.http import Http404, FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import logging
import json
import requests

from videos.forms import VideoForm
from videos.tasks import delete_s3_file, send_request_to_text_to_vid_api, send_test_request
from videos.utils import get_s3_client

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

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        status = None
        message = None

        if self.object.status == "processing":
            status, message = self.poll_video_status(self.object)

        context = self.get_context_data(object=self.object, status=status, message=message)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 🔽 Add your extra data here
        context["status"] = kwargs.get("status", None)
        context["message"] = kwargs.get("message", None)


        if self.object.status == "completed":

            # 🔽 Add pre-signed video URL
            s3 = get_s3_client()
            if s3:
                video = self.object
                try:
                    presigned_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': f"videos/{video.pk}.mp4"},
                        ExpiresIn=3600
                    )
                    context["video_url"] = presigned_url
                except Exception as e:
                    logger.error(f"Error generating S3 URL: {e}")
                    context["video_url_error"] = "Could not load video."
                    context["video_url"] = None
            else:
                context["video_url"] = None
                context["video_url_error"] = "Could not load video."
        else:
            context["video_url"] = None

        return context

    def poll_video_status(self, video):
        """
        Polls external API for latest status based on the video object.
        This is just a placeholder — add your logic.
        """

        try:
            response = requests.get(f"{settings.VIDEOAPI_BASE_URL}/status/{video.celery_task_id}")
            response.raise_for_status()
            data = response.json()

        except requests.RequestException as e:
            # Handle or log error
            logger.error(f"Error polling API: {e}")
            message = f"Error connecting to API"
            status = "error"
            return status, message

        else:

            status = data['status']
            message = data['message']

            return status, message

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
            video.s_three_url = None
            video.celery_task_id = None
            video.status = "uploaded"

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

        if instance.status == "completed":
            delete_s3_file.delay_on_commit(video_id=instance.pk)

        # Proceed with the standard delete operation
        return super().form_valid(form)

@login_required
def download_video(request, pk):

    # Get the file object
    video = get_object_or_404(Video, pk=pk, user=request.user)

    s3 = get_s3_client()

    if s3 is None:
        messages.error(request, "An error occurred")
        return redirect("video_detail", pk=video.pk)

    try:

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

@csrf_exempt
@require_POST
def video_complete_notification(request):

    payload = {}
    expected_api_key = settings.DJANGO_API_KEY
    auth_header = request.headers.get("Authorization")

    if not expected_api_key or not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or malformed Authorization header")
        return JsonResponse({"error": "Unauthorized"}, status=401)

    token = auth_header.split(" ", 1)[1]
    if token != expected_api_key:
        logger.warning("Invalid API key")
        return JsonResponse({"error": "Unauthorized"}, status=401)

    # Parse JSON payload
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON received, payload={payload}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    required_fields = ["video_id", "job_id", "status", "completed_at", "video_url", "error_message"]
    if not all(field in payload for field in required_fields):
        logger.error(f"Missing fields in payload: {payload}")
        return JsonResponse({"error": "Missing fields"}, status=400)

    logger.debug(payload)

    # Extract values
    video_id = payload["video_id"]
    job_id = payload["job_id"]
    status = payload["status"]
    completed_at = payload["completed_at"]
    video_url = payload["video_url"]
    error_message = payload["error_message"]

    video = Video.objects.get(pk=video_id)

    video.status = status

    if status == "completed":
        video.s_three_url = video_url

    if status == "error":
        logger.error(error_message)

    try:
        video.save()
    except Exception as e:
        logger.error(e)
        return JsonResponse({"error": "An error occurred"}, status=500)

    return JsonResponse({"message": "Webhook processed"}, status=200)