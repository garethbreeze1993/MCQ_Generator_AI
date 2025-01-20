import json
from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from langchain.chains.question_answering.stuff_prompt import messages
from torch.distributed.elastic.multiprocessing.redirects import redirect

from chatbot.models import Chat, Message
from chatbot.forms import ChatTitleForm



class MockLLMContent:

    def __init__(self, content):
        self.content = content


class ChatTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password')

        cls.random_user = User.objects.create_user(username='randomuser', password='random')

        cls.test_chat = Chat.objects.create(title='test chat', user=cls.test_user)

        for i in range(1, 9):
            llm_response = True if i % 2 == 0 else False
            m = Message.objects.create(
                message_text=f"Message_{i}", chat=cls.test_chat, order_number=i, llm_response=llm_response)
            setattr(cls, f'message_{i}', m)

        cls.message_1 = getattr(cls, 'message_1')
        cls.message_2 = getattr(cls, 'message_2')
        cls.message_3 = getattr(cls, 'message_3')
        cls.message_4 = getattr(cls, 'message_4')
        cls.message_5 = getattr(cls, 'message_5')
        cls.message_6 = getattr(cls, 'message_6')
        cls.message_7 = getattr(cls, 'message_7')
        cls.message_8 = getattr(cls, 'message_8')

    def setUp(self):
        # Every test needs a client.
        self.authenticated_client = Client()
        self.authenticated_client.login(username='testuser', password='password')
        self.unauthenticated_client = Client()

    def test_authenticated_client_get_all_chats(self):
        url = reverse("chat_index")
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['chats']), 1)
        self.assertEqual(response.context['chats'][0], ChatTestCase.test_chat)

    def test_unauthenticated_client_get_all_chats(self):
        url = reverse("chat_index")
        response = self.unauthenticated_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_authenticated_client_get_chat_detail_data(self):
        pk = ChatTestCase.test_chat.pk

        url = reverse("chat_detail", args=[pk])

        messages = Message.objects.filter(chat=ChatTestCase.test_chat).order_by('order_number')

        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chat'], ChatTestCase.test_chat)
        self.assertEqual(messages.count(), 8)
        self.assertEqual(len(response.context['llm_messages']), len(messages))
        self.assertEqual(list(response.context['llm_messages']), list(messages))

    def test_random_authenticated_client_get_chat_detail_fail(self):
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')

        pk = ChatTestCase.test_chat.pk

        url = reverse("chat_detail", args=[pk])
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_client_get_chat_detail_data(self):
        pk = ChatTestCase.test_chat.pk
        url = reverse("chat_detail", args=[pk])
        response = self.unauthenticated_client.get(url)

        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_new_chat_get_request_success(self):

        url = reverse("new_chat")
        # Simulate a GET request to the view
        response = self.authenticated_client.get(url)

        # Check that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, "chatbot/chatbot.html")

        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], ChatTitleForm)

        self.assertEqual(self.authenticated_client.session['lyl_messages'], [])
        self.assertEqual(self.authenticated_client.session['number_chats'], 1)

    def test_new_chat_get_request_unauthorised(self):
        url = reverse("new_chat")
        # Simulate a GET request to the view
        response = self.unauthenticated_client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch("chatbot.views.chatbot_response")
    def test_answer_input_success_first_msg(self, mock_chatbot_response):
        url = reverse("answer_user_input")
        user_message = "Hello World"
        llm_message = "Hello Human"
        llm_response = MockLLMContent(llm_message)
        mock_chatbot_response.return_value = llm_response
        response = self.authenticated_client.post(url, data={"user_msg": user_message}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), {"message": llm_message})

        message_dict = {f"user_msg": user_message, f"llm_msg": llm_message, "chat_number": 1}

        self.assertEqual(self.authenticated_client.session['number_chats'], 2)
        self.assertEqual(self.authenticated_client.session['lyl_messages'], [message_dict])
        mock_chatbot_response.assert_called_once_with(user_message)

    @patch("chatbot.views.chatbot_response")
    def test_answer_input_success_multiple_msg(self, mock_chatbot_response):
        url = reverse("answer_user_input")
        user_message = "Hello World multiple"
        llm_message = "Hello Human multiple"
        llm_response = MockLLMContent(llm_message)
        mock_chatbot_response.return_value = llm_response
        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_chats'] = 4
        session['lyl_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"user_msg": user_message}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), {"message": llm_message})

        message_dict = {f"user_msg": user_message, f"llm_msg": llm_message, "chat_number": 4}

        message_session.append(message_dict)

        self.assertEqual(self.authenticated_client.session['number_chats'], 5)
        self.assertEqual(self.authenticated_client.session['lyl_messages'], message_session)

        mock_chatbot_response.assert_called_once_with(user_message)

    @patch("chatbot.views.chatbot_response")
    def test_answer_input_unauthorised(self, mock_chatbot_response):
        url = reverse("answer_user_input")
        user_message = "Hello World"
        llm_message = "Hello Human"
        llm_response = MockLLMContent(llm_message)
        mock_chatbot_response.return_value = llm_response
        response = self.client.post(url, data={"user_msg": user_message}, content_type="application/json")
        self.assertEqual(response.status_code, 302)
        mock_chatbot_response.assert_not_called()

    def test_save_chat_success(self):
        url = reverse("save_chat")
        new_chat_title = 'Save Chat Test'
        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_chats'] = 4
        session['lyl_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 302)
        new_chat_queryset = Chat.objects.filter(title=new_chat_title, user=ChatTestCase.test_user)
        self.assertTrue(new_chat_queryset.exists())
        self.assertEqual(new_chat_queryset.count(), 1)
        new_chat_obj = new_chat_queryset.first()
        messages_queryset = Message.objects.filter(chat=new_chat_obj).order_by('order_number')
        self.assertEqual(messages_queryset.count(), 6)

        expected_msg_txt = ["user_msg_1", "llm_msg_1", "user_msg_2", "llm_msg_2", "user_msg_3", "llm_msg_3"]
        count = 0

        for message in messages_queryset:

            self.assertEqual(message.message_text, expected_msg_txt[count])

            message_txt = message.message_text.split("_")
            user = message_txt[0]
            number = message_txt[2]

            if user == "user":
                self.assertEqual(int(number) * 2 - 1, message.order_number)
            else:
                self.assertEqual(int(number) * 2, message.order_number)

            if message.order_number % 2 == 0:
                self.assertTrue(message.llm_response)
            else:
                self.assertFalse(message.llm_response)

            count += 1

    def test_save_form_not_valid(self):
        url = reverse("save_chat")
        new_chat_title = 'Save Chat Test dhbbbbbbsnjssssssssssssssss22888888888888888888dbbdbdbdbdbdbbdbdbhddhwkebwefbwedkbfhewfbefbwekfbfhjfbkrwfdkdjkdjdjjdjdjddjd'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_chats'] = 4
        session['lyl_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Please fix chat name")


    def test_save_form_error_save_chat(self):
        url = reverse("save_chat")
        new_chat_title = 'test chat'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_chats'] = 4
        session['lyl_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Error when saving chat")
        number_chat_queryset = Chat.objects.filter(title=ChatTestCase.test_chat.title, user=ChatTestCase.test_user)
        self.assertTrue(number_chat_queryset.exists())
        self.assertEqual(number_chat_queryset.count(), 1)

    def test_save_unauthenticated_user(self):
        url = reverse("save_chat")
        new_chat_title = 'test chat'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.unauthenticated_client.session
        session['number_chats'] = 4
        session['lyl_messages'] = message_session
        session.save()
        response = self.unauthenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 302)

    def test_delete_success(self):

        before_chats = Chat.objects.filter(user=ChatTestCase.test_user)
        before_count = before_chats.count()
        self.assertEqual(before_count, 1)
        before_chat = before_chats.first()
        pk = before_chat.pk
        before_messages = Message.objects.filter(chat=before_chat)
        before_messages_2 = Message.objects.filter(chat_id=pk)
        self.assertEqual(before_messages.count(), 8)
        self.assertEqual(before_messages_2.count(), 8)

        url = reverse("delete_chat", args=[pk])

        first_response = self.authenticated_client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, "chatbot/confirm_chat_delete.html")

        second_response = self.authenticated_client.post(url)
        self.assertEqual(second_response.status_code, 302)
        redirect_url = reverse("chat_index")
        self.assertEqual(second_response.url, redirect_url)

        after_delete_chat = Chat.objects.filter(pk=pk)
        self.assertFalse(after_delete_chat.exists())

        after_delete_messages = Message.objects.filter(chat_id=pk)
        self.assertFalse(after_delete_messages.exists())

    def test_delete_different_user(self):

        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')
        pk = ChatTestCase.test_chat.pk


        url = reverse("delete_chat", args=[pk])

        first_response = self.random_client.get(url)
        self.assertEqual(first_response.status_code, 404)

    def test_delete_unauthenticated_user(self):

        pk = ChatTestCase.test_chat.pk


        url = reverse("delete_chat", args=[pk])

        first_response = self.unauthenticated_client.get(url)
        self.assertEqual(first_response.status_code, 404)

