from django.urls import path

from . import views
from videos import views

urlpatterns = [
    path("", views.VideoListView.as_view(), name="video_index"),
    path('<int:pk>', views.VideoDetailView.as_view(), name='video_detail'),
    path("create_video", views.upload_video, name="create_video"),
    path('delete/<int:pk>', views.VideoDeleteView.as_view(), name='delete_video'),
    path("download_video/<int:pk>", views.download_video, name="download_video"),
    path("test_video", views.test_video, name="test_video"),
    path("complete", views.video_complete_notification, name="video_complete_notification"),
    path("notify", views.fastapi_status_view, name="fastapi_status_view")
]