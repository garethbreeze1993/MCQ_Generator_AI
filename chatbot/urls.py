from django.urls import path

from . import views
from chatbot import views

urlpatterns = [
    path("new_chat", views.ChatBotPageView.as_view(), name="new_chat")
]