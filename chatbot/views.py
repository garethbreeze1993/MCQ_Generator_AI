import logging
import json

from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

from chatbot.helpers import chatbot_response

logger = logging.getLogger("django_mcq")


class ChatBotPageView(LoginRequiredMixin, TemplateView):
    template_name = 'chatbot/chatbot.html'

@login_required(login_url='login')
def answer_user_input(request):

    post_data = json.loads(request.body.decode("utf-8"))

    user_message = post_data['user_msg']

    chatbot_res = chatbot_response(user_message)

    logger.debug(chatbot_res)

    return JsonResponse({"message": chatbot_res.content})