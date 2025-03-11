import json
from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from library.models import LibChat, LibMessage
from library.forms import LibDocForm, LibChatTitleForm, SaveLibChatTitleForm
# from chatbot.forms import ChatTitleForm


class LibraryTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password')

        cls.random_user = User.objects.create_user(username='randomuser', password='random')

        cls.test_chat = LibChat.objects.create(title='test chat', user=cls.test_user)

        for i in range(1, 9):
            llm_response = True if i % 2 == 0 else False
            m = LibMessage.objects.create(
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

        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')


    def test_authenticated_client_get_all_lib_chats(self):
        url = reverse("library_index")
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['chats']), 1)
        self.assertEqual(response.context['chats'][0], LibraryTestCase.test_chat)
        self.assertTemplateUsed(response, "library/library_index.html")

    def test_authenticated_client_get_all_lib_chats_different_user(self):
        url = reverse("library_index")
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['chats']), 0)
        self.assertTemplateUsed(response, "library/library_index.html")

    def test_unauthenticated_client_get_all_lib_chats(self):
        url = reverse("library_index")
        response = self.unauthenticated_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_authenticated_client_get_libchat_detail_data(self):
        pk = LibraryTestCase.test_chat.pk

        url = reverse("lib_chat_detail", args=[pk])

        messages = LibMessage.objects.filter(chat=LibraryTestCase.test_chat).order_by('order_number')

        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chat'], LibraryTestCase.test_chat)
        self.assertEqual(messages.count(), 8)
        self.assertEqual(len(response.context['llm_messages']), len(messages))
        self.assertEqual(list(response.context['llm_messages']), list(messages))

    def test_random_authenticated_client_get_libchat_detail_fail(self):
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')

        pk = LibraryTestCase.test_chat.pk

        url = reverse("lib_chat_detail", args=[pk])
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_client_get_libchat_detail_data(self):
        pk = LibraryTestCase.test_chat.pk
        url = reverse("lib_chat_detail", args=[pk])
        response = self.unauthenticated_client.get(url)

        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_new_libchat_get_request_success(self):

        url = reverse("new_lib_chat")
        # Simulate a GET request to the view
        response = self.authenticated_client.get(url)

        # Check that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, "library/lib_chatbot.html")

        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LibChatTitleForm)

        self.assertEqual(self.authenticated_client.session['library_messages'], [])
        self.assertEqual(self.authenticated_client.session['number_lib_chats'], 1)

    def test_new_libchat_get_request_unauthorised(self):
        url = reverse("new_lib_chat")
        # Simulate a GET request to the view
        response = self.unauthenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
