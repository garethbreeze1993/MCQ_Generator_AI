from django.urls import path

from . import views
from library import views

urlpatterns = [
    path("", views.LibChatListView.as_view(), name="library_index"),
    path('<int:pk>', views.get_lib_chat_data, name='lib_chat_detail'),
    path("documents", views.LibDocListView.as_view(), name="lib_doc_list"),
    path("new_chat", views.lib_chatbot_new_chat, name="new_lib_chat"),
    path("upload_documents", views.upload_document, name="upload_document"),

]