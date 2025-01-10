from django.urls import path

from . import views
from chatbot import views

urlpatterns = [
    path("new_chat", views.ChatBotPageView.as_view(), name="new_chat"),
    path("answer_user", views.answer_user_input, name="answer_user_input")
]