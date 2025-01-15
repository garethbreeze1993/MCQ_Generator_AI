from django.urls import path

from . import views
from chatbot import views

urlpatterns = [
    path("", views.ChatListView.as_view(), name="chat_index"),
    path('<int:pk>', views.get_chat_data, name='chat_detail'),
    path("new_chat", views.chatbot_new_chat, name="new_chat"),
    path("answer_user", views.answer_user_input, name="answer_user_input"),
    path("save_chat", views.save_chat, name="save_chat"),
    path('delete/<int:pk>', views.ChatDeleteView.as_view(), name='delete_chat')
]