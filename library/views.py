import logging
import json
import os

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse, Http404
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy

from chatbot.forms import ChatTitleForm
from library.forms import LibDocForm
from library.models import LibChat, LibMessage, LibDocuments, LibDocumentEmbeddings
from library.helpers import upload_document_to_library, delete_document_from_library


logger = logging.getLogger("django_mcq")


class LibChatListView(LoginRequiredMixin, ListView):
    model = LibChat
    paginate_by = 10  # if pagination is desired
    template_name = 'library/library_index.html'  # Specify your template name
    context_object_name = 'chats'  # The variable to use in the template

    def get_queryset(self):
        # Filter quizzes by the current logged-in user
        return LibChat.objects.filter(user=self.request.user)

@login_required(login_url='login')
def get_lib_chat_data(request, pk):

    logger.debug("testing output")
    logger.debug(pk)
    # Get the quiz by pk or return 404 if not found
    chat = get_object_or_404(LibChat, pk=pk, user=request.user)

    # # Check if the logged-in user is associated with the quiz
    # if quiz.user != request.user:
    #     return HttpResponseForbidden("You are not allowed to access this quiz.")

    logger.debug(chat)

    # Get the questions associated with this quiz
    chat_messages = LibMessage.objects.filter(chat=chat).order_by('order_number')



    # Send the structured data to the template
    context = {
        'chat': chat,
        'llm_messages': chat_messages
    }

    return render(request, 'library/lib_chat_detail.html', context)

class LibDocListView(LoginRequiredMixin, ListView):
    model = LibDocuments
    paginate_by = 10  # if pagination is desired
    template_name = 'library/lib_doc_list.html'  # Specify your template name
    context_object_name = 'documents'  # The variable to use in the template

    def get_queryset(self):
        # Filter quizzes by the current logged-in user
        return LibDocuments.objects.filter(user=self.request.user)

@login_required
def lib_chatbot_new_chat(request):
    request.session['lyl_messages'] = []
    request.session['number_chats'] = 1
    return render(request=request, template_name='library/lib_chatbot.html', context={'form': ChatTitleForm()})

@login_required(login_url='login')
def upload_document(request):
    form = None

    if request.method == "POST":

        logger.info('hitsa')

        form = LibDocForm(request.POST, request.FILES)

        if form.is_valid():

            latest_doc = LibDocuments.objects.filter(user=request.user).order_by('-datetime_added').first()

            if latest_doc:
                latest_embedding = LibDocumentEmbeddings.objects.filter(document=latest_doc).first()
                last_id = latest_embedding.end_id
            else:
                last_id = 0

            lib_doc = form.save(commit=False)  # Don't save yet
            lib_doc.user = request.user  # Assign the logged-in user
            lib_doc.name = lib_doc.upload_file.name  # Save original filename

            unique_user = f'user_{request.user.id}'

            new_id = last_id + 1

            try:
                with transaction.atomic():
                    lib_doc.save()
            except Exception as e:
                logger.error(e)
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, "library/lib_upload_doc.html", {"form": form})

            file_path = os.path.join(settings.MEDIA_ROOT, lib_doc.upload_file.name)

            try:
                end_id = upload_document_to_library(file_path=file_path, unique_user=unique_user, new_id=new_id)

            except Exception as e:
                logger.error(e)
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, "library/lib_upload_doc.html", {"form": form})

            lib_doc_embeddings = LibDocumentEmbeddings()
            lib_doc_embeddings.document = lib_doc
            lib_doc_embeddings.start_id = new_id
            lib_doc_embeddings.end_id = end_id

            try:
                lib_doc_embeddings.save()
            except Exception as e:
                logger.error(e)
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, "library/lib_upload_doc.html", {"form": form})

            messages.success(request, "Data saved successfully!")
            return redirect("lib_doc_list")  # Redirect after saving

        else:
            logger.error(form.errors)
            return render(request, "library/lib_upload_doc.html", {"form": form})

    else:
        # Request method is GET
        form = LibDocForm()

        return render(request, "library/lib_upload_doc.html", {"form": form})


class LibDocumentsDetailView(LoginRequiredMixin, DetailView):
    model = LibDocuments
    template_name = "library/libdocuments_detail.html"
    context_object_name = "document"

    def get_queryset(self):
        # Ensure users can only access their own documents
        return LibDocuments.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs.get("pk"))

class LibraryDocumentsDeleteView(LoginRequiredMixin, DeleteView):
    # specify the model you want to use
    model = LibDocuments
    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_url = reverse_lazy("lib_doc_list")
    template_name = "library/confirm_doc_delete.html"

    def get_queryset(self):
        """
        Limit the queryset to quizzes owned by the logged-in user.
        """
        return LibDocuments.objects.filter(user=self.request.user)

    def handle_no_permission(self):
        """
        Handle unauthorized access attempts.
        """
        raise Http404("You do not have permission to delete this quiz.")

    def form_valid(self, form):
        """
        Custom logic before deletion.
        """

        logger.info('inside form valid method')

        instance = self.get_object()

        number_documents = LibDocuments.objects.filter(user=self.request.user).count()

        unique_user = f'user_{self.request.user.id}'

        delete_document_from_library(
            number_of_documents=number_documents, document_pk=instance.pk, unique_user=unique_user)


        # Perform custom logic, e.g., delete the uploaded file from storage
        if instance.upload_file:
            file_path = instance.upload_file.path
            if os.path.exists(file_path):
                os.remove(file_path)

        # Perform any other necessary cleanup

        # Proceed with the standard delete operation
        return super().form_valid(form)


