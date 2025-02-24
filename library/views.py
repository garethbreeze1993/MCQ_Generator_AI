import logging
import json

from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy

from chatbot.forms import ChatTitleForm
from library.forms import LibDocForm
from library.models import LibChat, LibMessage, LibDocuments


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
    if request.method == 'GET':
        form = LibDocForm()
    else:
        return HttpResponseForbidden('DONT HIT THIS')
    return render(request, "library/lib_upload_doc.html", {"form": form})
