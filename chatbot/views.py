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

    message_dict = {f"user_msg": user_message, f"llm_msg": chatbot_res_content, "chat_number": chat_number}

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

    logger.debug(request.POST['name_title'])
    logger.debug(request.session["lyl_messages"])
    logger.debug(request.session["number_chats"])

    new_chat = Chat()
    new_chat.user = request.user
    new_chat.title = request.POST['name_title']

    try:
        new_chat.save()
    except Exception as e:
        logger.error(e)
        messages.error(request, f"An error occurred: {str(e)}")
        return JsonResponse({"error": "Error when saving chat"}, status=500)

    for message in request.session["lyl_messages"]:

        user_chat_number = message["chat_number"] * 2 - 1
        llm_chat_number = message["chat_number"] * 2

        new_user_message = Message()
        new_llm_message = Message()

        new_user_message.chat = new_chat
        new_llm_message.chat = new_chat

        new_user_message.message_text = message['user_msg']
        new_user_message.order_number = user_chat_number
        new_user_message.llm_response = False

        new_llm_message.message_text = message['llm_msg']
        new_llm_message.order_number = llm_chat_number
        new_llm_message.llm_response = True

        try:
            new_user_message.save()
            new_llm_message.save()

        except Exception as e:
            logger.error(e)
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({"error": "Error when saving Messaged"}, status=500)

    messages.success(request, "Data saved successfully!")
    return redirect("index")

@login_required(login_url='login')
def get_chat_data(request, pk):

    logger.debug("testing output")
    logger.debug(pk)
    # Get the quiz by pk or return 404 if not found
    chat = get_object_or_404(Chat, pk=pk, user=request.user)

    # # Check if the logged-in user is associated with the quiz
    # if quiz.user != request.user:
    #     return HttpResponseForbidden("You are not allowed to access this quiz.")

    logger.debug(chat)

    # Get the questions associated with this quiz
    chat_messages = Message.objects.filter(chat=chat).order_by('order_number')



    # Send the structured data to the template
    context = {
        'chat': chat,
        'llm_messages': chat_messages
    }

    return render(request, 'chatbot/chat_detail.html', context)

class ChatDeleteView(LoginRequiredMixin, DeleteView):
    # specify the model you want to use
    model = Chat
    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_url = reverse_lazy("chat_index")
    template_name = "chatbot/confirm_chat_delete.html"
    def get_queryset(self):
        """
        Limit the queryset to quizzes owned by the logged-in user.
        """
        return Chat.objects.filter(user=self.request.user)
    def handle_no_permission(self):
        """
        Handle unauthorized access attempts.
        """
        raise Http404("You do not have permission to delete this quiz.")