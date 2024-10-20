from django.urls import path

from . import views

urlpatterns = [
    path("", views.QuizListView.as_view(), name="index"),
    path('<pk>/', views.get_quiz_data, name='q_detail'),
]