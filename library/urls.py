from django.urls import path

from . import views
from library import views

urlpatterns = [
    path("", views.LibChatListView.as_view(), name="library_index"),
    path('<int:pk>', views.get_lib_chat_data, name='lib_chat_detail'),
    path("documents", views.LibDocListView.as_view(), name="lib_doc_list"),
    path("new_chat", views.lib_chatbot_new_chat, name="new_lib_chat"),
    path("upload_documents", views.upload_document, name="upload_document"),
    path('document/<int:pk>/', views.LibDocumentsDetailView.as_view(), name='libdocuments_detail'),
    path('delete/document/<int:pk>', views.LibraryDocumentsDeleteView.as_view(), name='delete_document'),
    path("answer_user", views.answer_user_input_library, name="answer_user_input_lib"),
    path("save_chat", views.save_lib_chat, name="save_lib_chat"),
    path("download_file/<int:pk>", views.download_file, name="download_file"),
    path('delete/<int:pk>', views.LibChatDeleteView.as_view(), name='delete_lib_chat')

]