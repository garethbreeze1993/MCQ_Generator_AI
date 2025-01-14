import logging
import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic.list import ListView
from django.http import HttpResponseForbidden

from chatbot.helpers import chatbot_response
from chatbot.models import Chat, Message
from chatbot.forms import ChatTitleForm


logger = logging.getLogger("django_mcq")


class ChatListView(LoginRequiredMixin, ListView):
    model = Chat
    paginate_by = 10  # if pagination is desired
    template_name = 'chatbot/chatbot_index.html'  # Specify your template name
    context_object_name = 'chats'  # The variable to use in the template

    def get_queryset(self):
        # Filter quizzes by the current logged-in user
        return Chat.objects.filter(user=self.request.user)


@login_required
def chatbot_new_chat(request):
    request.session['lyl_messages'] = []
    request.session['number_chats'] = 1
    return render(request=request, template_name='chatbot/chatbot.html', context={'form': ChatTitleForm()})


@login_required(login_url='login')
def answer_user_input(request):

    post_data = json.loads(request.body.decode("utf-8"))

    try:
        chat_number = request.session["number_chats"]
    except KeyError:
        chat_number = 1
    else:
        chat_number = int(chat_number)


    user_message = post_data['user_msg']

    chatbot_res = chatbot_response(user_message)

    chatbot_res_content = chatbot_res.content

    message_dict = {f"user_msg_{chat_number}": user_message, f"llm_msg_{chat_number}": chatbot_res_content}

    chat_messages = request.session.get("lyl_messages", [])
    chat_messages.append(message_dict)
    request.session["lyl_messages"] = chat_messages  # Save back to the session

    new_chat_number = chat_number + 1
    request.session["number_chats"] = new_chat_number

    logger.debug("This is session at end of logic")

    logger.debug(request.session["lyl_messages"])
    logger.debug(request.session["number_chats"])

    return JsonResponse({"message": chatbot_res_content})

@login_required(login_url='login')
def save_chat(request):
    if request.method != 'POST':
        return HttpResponseForbidden('DONT HIT THIS')
    logger.info(request.POST['name_title'])
    logger.info(request.session["lyl_messages"])
    logger.info(request.session["number_chats"])
    messages.success(request, "Data saved successfully!")
    return redirect("index")