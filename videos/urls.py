from django.urls import path

from . import views
from videos import views

urlpatterns = [
    path("", views.VideoListView.as_view(), name="video_index"),
    path('<int:pk>', views.VideoDetailView.as_view(), name='video_detail'),
    path("create_video", views.upload_video, name="create_video"),
    path('delete/<int:pk>', views.VideoDeleteView.as_view(), name='delete_video')
]