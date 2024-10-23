from django.urls import path

from . import views
from .views import create_quiz

urlpatterns = [
    path("", views.QuizListView.as_view(), name="index"),
    path('<int:pk>', views.get_quiz_data, name='q_detail'),
    path('create', create_quiz, name='create_quiz'),
    path('generate', views.generate_quiz, name='generate_quiz'),
]