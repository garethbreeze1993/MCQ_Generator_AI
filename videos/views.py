from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.http import Http404

import logging

from videos.forms import VideoForm

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