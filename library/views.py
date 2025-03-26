import logging
import json
import os

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse, Http404, FileResponse
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy

from library.forms import LibDocForm, LibChatTitleForm, SaveLibChatTitleForm
from library.models import LibChat, LibMessage, LibDocuments, LibDocumentEmbeddings
from library.helpers import answer_user_message_library
from library.tasks import upload_document_to_library, delete_document_from_library
from library.utils import get_list_of_ids_for_chroma_deletion


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

    # Get the quiz by pk or return 404 if not found
    chat = get_object_or_404(LibChat, pk=pk, user=request.user)

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
    request.session['library_messages'] = []
    request.session['number_lib_chats'] = 1

    number_of_docs = LibDocuments.objects.filter(user=request.user, status="completed").count()

    if number_of_docs == 0:
        messages.error(request, "Please upload some documents before using the chatbot")
        return redirect("lib_doc_list")

    form = LibChatTitleForm(user=request.user)
    context_dict = {'form': form}
    return render(request=request, template_name='library/lib_chatbot.html', context=context_dict)

@login_required(login_url='login')
def upload_document(request):
    form = None

    if request.method == "POST":

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
            lib_doc.status = "uploaded"

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


            upload_document_to_library.delay_on_commit(file_path=file_path, unique_user=unique_user, new_id=new_id,
                                                    document_pk=lib_doc.pk)


            lib_doc_embeddings = LibDocumentEmbeddings()
            lib_doc_embeddings.document = lib_doc
            lib_doc_embeddings.start_id = new_id

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

        if number_documents == 1:
            list_of_ids = None
        else:
            lib_doc = LibDocumentEmbeddings.objects.get(document_id=instance.pk)

            start_id = lib_doc.start_id

            end_id = lib_doc.end_id

            list_of_ids = get_list_of_ids_for_chroma_deletion(start_id=start_id, end_id=end_id)

        delete_document_from_library.delay_on_commit(
            number_of_documents=number_documents, list_of_ids=list_of_ids, unique_user=unique_user)


        # Perform custom logic, e.g., delete the uploaded file from storage
        if instance.upload_file:
            file_path = instance.upload_file.path
            if os.path.exists(file_path):
                os.remove(file_path)

        # Perform any other necessary cleanup

        # Proceed with the standard delete operation
        return super().form_valid(form)

@login_required(login_url='login')
def answer_user_input_library(request):

    post_data = json.loads(request.body.decode("utf-8"))

    try:
        chat_number = request.session["number_lib_chats"]
    except KeyError:
        chat_number = 1
    else:
        chat_number = int(chat_number)


    user_message = post_data['user_msg']
    unique_user = f'user_{request.user.id}'

    user_docs = post_data['user_docs']

    filter_docs = []

    for doc in user_docs:
        lib_doc = LibDocuments.objects.filter(user=request.user, pk=doc).first()
        file_path = os.path.join(settings.MEDIA_ROOT, lib_doc.upload_file.name)
        filter_docs.append(file_path)

    try:
        chatbot_res = answer_user_message_library(user_message, unique_user, filter_docs)
    except Exception as e:
        logger.error(e)
        return JsonResponse({"message": "Problem with chatbot response please contact the System Administrator"})

    chatbot_res_content = chatbot_res.content

    message_dict = {f"user_msg": user_message, f"llm_msg": chatbot_res_content, "chat_number": chat_number}

    chat_messages = request.session.get("library_messages", [])
    chat_messages.append(message_dict)
    request.session["library_messages"] = chat_messages  # Save back to the session

    new_chat_number = chat_number + 1
    request.session["number_lib_chats"] = new_chat_number

    logger.debug("This is session at end of logic lib")

    logger.debug(request.session["library_messages"])
    logger.debug(request.session["number_lib_chats"])

    return JsonResponse({"message": chatbot_res_content})


@login_required(login_url='login')
def save_lib_chat(request):
    if request.method != 'POST':
        return HttpResponseForbidden('DONT HIT THIS')

    logger.debug(request.POST['name_title'])
    logger.debug(request.session["library_messages"])
    logger.debug(request.session["number_lib_chats"])

    submitted_form = SaveLibChatTitleForm(request.POST)

    if not submitted_form.is_valid():
        logger.error(submitted_form.errors)
        messages.error(request, 'Please fix chat name')
        return JsonResponse({"error": "Please fix chat name"}, status=400)

    new_chat = LibChat()
    new_chat.user = request.user
    new_chat.title = submitted_form.cleaned_data['name_title']

    try:
        new_chat.save()
    except Exception as e:
        logger.error(e)
        messages.error(request, f"An error occurred: {str(e)}")
        return JsonResponse({"error": "Error when saving chat"}, status=500)

    for message in request.session["library_messages"]:

        user_chat_number = message["chat_number"] * 2 - 1
        llm_chat_number = message["chat_number"] * 2

        new_user_message = LibMessage()
        new_llm_message = LibMessage()

        new_user_message.chat = new_chat
        new_llm_message.chat = new_chat

        new_user_message.message_text = message['user_msg']
        new_user_message.order_number = user_chat_number
        new_user_message.llm_response = False

        new_llm_message.message_text = message['llm_msg']
        new_llm_message.order_number = llm_chat_number
        new_llm_message.llm_response = True

        try:
            # Unable to test as unsure how I will hit this in a unit test
            new_user_message.save()
            new_llm_message.save()

        except Exception as e:
            logger.error(e)
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({"error": "Error when saving Messaged"}, status=500)

    messages.success(request, "Data saved successfully!")
    return redirect("library_index")


@login_required
def download_file(request, pk):
    # Get the file object
    file_obj = get_object_or_404(LibDocuments, pk=pk, user=request.user)

    # Ensure the file exists
    if not file_obj.upload_file:
        raise Http404("File not found")

    # Return the file response
    response = FileResponse(file_obj.upload_file.open('rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{file_obj.upload_file.name}"'
    return response

class LibChatDeleteView(LoginRequiredMixin, DeleteView):
    # specify the model you want to use
    model = LibChat
    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_url = reverse_lazy("library_index")
    template_name = "chatbot/confirm_chat_delete.html"

    def get_queryset(self):
        """
        Limit the queryset to quizzes owned by the logged-in user.
        """
        return LibChat.objects.filter(user=self.request.user)

    def handle_no_permission(self):
        """
        Handle unauthorized access attempts.
        """
        raise Http404("You do not have permission to delete this quiz.")
