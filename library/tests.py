from io import BytesIO
import json
import os
import shutil
from unittest import TestCase as unittestTestCase
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.urls import reverse

from library.models import LibChat, LibMessage, LibDocuments, LibDocumentEmbeddings
from library.forms import LibDocForm, LibChatTitleForm, SaveLibChatTitleForm
from library.utils import get_final_id, get_list_of_ids_for_chroma_deletion, get_lists_for_chroma_upsert
from chatbot.tests import MockLLMContent
# from chatbot.forms import ChatTitleForm

class MockLangchainDocument:

    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata



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

        pdf_content = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                       b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                       b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                       b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                       b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        pdf_content_2 = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                      b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                      b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                      b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                      b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        test_pdf = SimpleUploadedFile(
            name='test_document.pdf',
            content=pdf_content,
            content_type='application/pdf'
        )

        test_pdf_2 = SimpleUploadedFile(
            name='test_document_2.pdf',
            content=pdf_content_2,
            content_type='application/pdf'
        )

        cls.document_1 = LibDocuments.objects.create(name='test_document.pdf', user=cls.test_user,
                                                     upload_file=test_pdf)

        cls.document_2 = LibDocuments.objects.create(name='test_document_2.pdf', user=cls.test_user,
                                                     upload_file=test_pdf_2)

        cls.document_embedding_1 = LibDocumentEmbeddings.objects.create(document=cls.document_1, start_id=1,
                                                                        end_id=271)
        cls.document_embedding_1 = LibDocumentEmbeddings.objects.create(document=cls.document_2, start_id=272,
                                                                       end_id=341)

    @classmethod
    def tearDownClass(cls):
        unique_test_user = f'user_{LibraryTestCase.test_user.id}'
        file_path = os.path.join(settings.MEDIA_ROOT, unique_test_user)

        random_test_user = f'user_{LibraryTestCase.random_user.id}'
        file_path_two = os.path.join(settings.MEDIA_ROOT, random_test_user)

        # Clean up after all tests have run
        shutil.rmtree(file_path)
        shutil.rmtree(file_path_two)

        # Call the parent's tearDownClass
        super().tearDownClass()

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

    @patch("library.views.answer_user_message_library")
    def test_answer_input_lib_success_first_msg(self, mock_chatbot_response):
        url = reverse("answer_user_input_lib")
        user_message = "Hello World"
        llm_message = "Hello Human"
        llm_response = MockLLMContent(llm_message)
        user_docs = []
        unique_user = f'user_{LibraryTestCase.test_user.id}'
        mock_chatbot_response.return_value = llm_response
        response = self.authenticated_client.post(url, data={"user_msg": user_message, "user_docs": user_docs},
                                                  content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), {"message": llm_message})

        message_dict = {f"user_msg": user_message, f"llm_msg": llm_message, "chat_number": 1}

        self.assertEqual(self.authenticated_client.session['number_lib_chats'], 2)
        self.assertEqual(self.authenticated_client.session['library_messages'], [message_dict])
        mock_chatbot_response.assert_called_once_with(user_message, unique_user, [])

    @patch("library.views.answer_user_message_library")
    def test_answer_input_lib_success_multiple_msg(self, mock_chatbot_response):
        url = reverse("answer_user_input_lib")
        user_message = "Hello World multiple"
        llm_message = "Hello Human multiple"
        llm_response = MockLLMContent(llm_message)
        mock_chatbot_response.return_value = llm_response
        unique_user = f'user_{LibraryTestCase.test_user.id}'
        user_docs = [LibraryTestCase.document_1.pk, LibraryTestCase.document_2.pk]

        filter_docs = []

        for doc in user_docs:
            lib_doc = LibDocuments.objects.filter(user=LibraryTestCase.test_user, pk=doc).first()
            file_path = os.path.join(settings.MEDIA_ROOT, lib_doc.upload_file.name)
            filter_docs.append(file_path)

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"user_msg": user_message, "user_docs": user_docs}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), {"message": llm_message})

        message_dict = {f"user_msg": user_message, f"llm_msg": llm_message, "chat_number": 4}

        message_session.append(message_dict)

        self.assertEqual(self.authenticated_client.session['number_lib_chats'], 5)
        self.assertEqual(self.authenticated_client.session['library_messages'], message_session)

        mock_chatbot_response.assert_called_once_with(user_message, unique_user, filter_docs)

    @patch("library.views.answer_user_message_library")
    def test_answer_input_lib_chatbot_response_raises_exception(self, mock_chatbot_response):
        url = reverse("answer_user_input_lib")
        user_message = "Hello World multiple"
        mock_chatbot_response.side_effect = Exception
        user_docs = []
        unique_user = f'user_{LibraryTestCase.test_user.id}'
        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"user_msg": user_message, "user_docs": user_docs}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')),
                         {"message": "Problem with chatbot response please contact the System Administrator"})

        mock_chatbot_response.assert_called_once_with(user_message, unique_user, [])

    @patch("library.views.answer_user_message_library")
    def test_answer_input_lib_unauthorised(self, mock_chatbot_response):
        url = reverse("answer_user_input_lib")
        user_message = "Hello World"
        llm_message = "Hello Human"
        llm_response = MockLLMContent(llm_message)
        user_docs = []
        mock_chatbot_response.return_value = llm_response
        response = self.client.post(url, data={"user_msg": user_message, "user_docs": user_docs}, content_type="application/json")
        self.assertEqual(response.status_code, 302)
        mock_chatbot_response.assert_not_called()

    def test_save_lib_chat_success(self):
        url = reverse("save_lib_chat")
        new_chat_title = 'Save Lib Chat Test'
        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 302)
        new_chat_queryset = LibChat.objects.filter(title=new_chat_title, user=LibraryTestCase.test_user)
        self.assertTrue(new_chat_queryset.exists())
        self.assertEqual(new_chat_queryset.count(), 1)
        new_chat_obj = new_chat_queryset.first()
        messages_queryset = LibMessage.objects.filter(chat=new_chat_obj).order_by('order_number')
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

    def test_save_lib_form_not_valid(self):
        url = reverse("save_lib_chat")
        new_chat_title = 'Save Chat Test dhbbbbbbsnjssssssssssssssss22888888888888888888dbbdbdbdbdbdbbdbdbhddhwkebwefbwedkbfhewfbefbwekfbfhjfbkrwfdkdjkdjdjjdjdjddjd'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Please fix chat name")

    def test_save_lib_form_error_save_chat(self):
        url = reverse("save_lib_chat")
        new_chat_title = 'test chat'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.authenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.authenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Error when saving chat")
        number_chat_queryset = LibChat.objects.filter(title=LibraryTestCase.test_chat.title, user=LibraryTestCase.test_user)
        self.assertTrue(number_chat_queryset.exists())
        self.assertEqual(number_chat_queryset.count(), 1)

    def test_save_lib_unauthenticated_user(self):
        url = reverse("save_lib_chat")
        new_chat_title = 'test chat22'

        message_session = [{f"user_msg": "user_msg_1", f"llm_msg": "llm_msg_1", "chat_number": 1},
                           {f"user_msg": "user_msg_2", f"llm_msg": "llm_msg_2", "chat_number": 2},
                           {f"user_msg": "user_msg_3", f"llm_msg": "llm_msg_3", "chat_number": 3}]
        session = self.unauthenticated_client.session
        session['number_lib_chats'] = 4
        session['library_messages'] = message_session
        session.save()
        response = self.unauthenticated_client.post(url, data={"name_title": new_chat_title})
        self.assertEqual(response.status_code, 302)

    def test_lib_delete_different_user(self):

        pk = LibraryTestCase.test_chat.pk

        url = reverse("delete_lib_chat", args=[pk])

        first_response = self.random_client.get(url)
        self.assertEqual(first_response.status_code, 404)

    def test_lib_delete_unauthenticated_user(self):

        pk = LibraryTestCase.test_chat.pk

        url = reverse("delete_lib_chat", args=[pk])

        first_response = self.unauthenticated_client.get(url)
        self.assertEqual(first_response.status_code, 404)

    def test_lib_delete_success(self):

        before_chats = LibChat.objects.filter(user=LibraryTestCase.test_user)
        before_count = before_chats.count()
        self.assertEqual(before_count, 1)
        before_chat = before_chats.first()
        pk = before_chat.pk
        before_messages = LibMessage.objects.filter(chat=before_chat)
        before_messages_2 = LibMessage.objects.filter(chat_id=pk)
        self.assertEqual(before_messages.count(), 8)
        self.assertEqual(before_messages_2.count(), 8)

        url = reverse("delete_lib_chat", args=[pk])

        first_response = self.authenticated_client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, "chatbot/confirm_chat_delete.html")

        second_response = self.authenticated_client.post(url)
        self.assertEqual(second_response.status_code, 302)
        redirect_url = reverse("library_index")
        self.assertEqual(second_response.url, redirect_url)

        after_delete_chat = LibChat.objects.filter(pk=pk)
        self.assertFalse(after_delete_chat.exists())

        after_delete_messages = LibMessage.objects.filter(chat_id=pk)
        self.assertFalse(after_delete_messages.exists())

    def test_authenticated_client_get_libdoc_detail_data(self):
        pk = LibraryTestCase.document_1.pk

        url = reverse("libdocuments_detail", args=[pk])

        response = self.authenticated_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['document'], LibraryTestCase.document_1)
        self.assertTemplateUsed(response, "library/libdocuments_detail.html")

    def test_random_authenticated_client_get_libdoc_detail_fail(self):

        pk = LibraryTestCase.test_chat.pk

        url = reverse("libdocuments_detail", args=[pk])
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_client_get_libdoc_detail_data(self):
        pk = LibraryTestCase.test_chat.pk
        url = reverse("libdocuments_detail", args=[pk])
        response = self.unauthenticated_client.get(url)

        # Client not logged in so will get 302
        self.assertEqual(response.status_code, 302)

    def test_authenticated_client_get_all_lib_docs(self):
        url = reverse("lib_doc_list")
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['documents']), 2)
        self.assertEqual(response.context['documents'][0], LibraryTestCase.document_1)
        self.assertTemplateUsed(response, 'library/lib_doc_list.html')

    def test_authenticated_client_get_all_lib_docs_different_user(self):
        url = reverse("lib_doc_list")
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['documents']), 0)
        self.assertTemplateUsed(response, 'library/lib_doc_list.html')

    def test_unauthenticated_client_get_all_lib_docs(self):
        url = reverse("lib_doc_list")
        response = self.unauthenticated_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_download_file_authenticated_owner(self):
        """Test that an authenticated user can download their own file"""

        # Get the URL for downloading the file
        url = reverse('download_file', args=[LibraryTestCase.document_1.pk])

        # Make the request
        response = self.authenticated_client.get(url)

        # Check response status and headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))

    def test_download_file_authenticated_not_owner(self):
        """Test that an authenticated user cannot download another user's file"""

        # Get the URL for downloading the file
        url = reverse('download_file', args=[LibraryTestCase.document_1.pk])

        # Make the request
        response = self.random_client.get(url)

        # Should return 404 for security (not showing that the file exists but user doesn't have access)
        self.assertEqual(response.status_code, 404)

    def test_download_file_not_authenticated(self):
        """Test that an unauthenticated user cannot download files"""
        # Get the URL for downloading the file
        url = reverse('download_file', args=[LibraryTestCase.document_1.pk])

        # Make the request without logging in
        response = self.unauthenticated_client.get(url)

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_download_nonexistent_file(self):
        """Test behavior when trying to download a file that doesn't exist"""

        # Try to access a non-existent file ID
        nonexistent_id = 999
        url = reverse('download_file', args=[nonexistent_id])

        # Make the request
        response = self.authenticated_client.get(url)

        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_upload_document_get_request_authorised(self):

        url = reverse("upload_document")
        # Simulate a GET request to the view
        response = self.authenticated_client.get(url)

        # Check that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, "library/lib_upload_doc.html")

        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LibDocForm)

    def test_upload_document_get_request_unauthorised(self):
        url = reverse("upload_document")
        # Simulate a GET request to the view
        response = self.unauthenticated_client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_upload_document_post_request_form_not_valid(self):
        url = reverse("upload_document")
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"
        post_data = {"upload_file": mock_file}
        response = self.authenticated_client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        # Check that the correct template is used
        self.assertTemplateUsed(response, "library/lib_upload_doc.html")
        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LibDocForm)
        self.assertTrue(response.context['form'].errors)

    @patch("library.views.upload_document_to_library")
    def test_upload_document_chroma_upload_fail(self, chroma_upload_func):
        url = reverse("upload_document")
        pdf_content_test = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                         b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                         b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                         b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                         b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        mock_file_name = 'test_document_inside_test.pdf'

        mock_pdf = SimpleUploadedFile(
            name=mock_file_name,
            content=pdf_content_test,
            content_type='application/pdf'
        )
        chroma_upload_func.side_effect = Exception
        post_data = {"upload_file": mock_pdf}
        response = self.authenticated_client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        # Check that the correct template is used
        self.assertTemplateUsed(response, "library/lib_upload_doc.html")
        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LibDocForm)
        self.assertFalse(response.context['form'].errors)

        documents = LibDocuments.objects.filter(name=mock_file_name, user=LibraryTestCase.test_user)
        self.assertFalse(documents.exists())
        self.assertEqual(documents.count(), 0)

    @patch("library.views.upload_document_to_library")
    def test_upload_document_lib_embeddings_fail_random_user_no_embeddings(self, chroma_upload_func):
        url = reverse("upload_document")
        pdf_content_test = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                            b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                            b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                            b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                            b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        mock_file_name = 'test_document_inside_test.pdf'

        mock_pdf = SimpleUploadedFile(
            name=mock_file_name,
            content=pdf_content_test,
            content_type='application/pdf'
        )
        chroma_upload_func.return_value = None
        post_data = {"upload_file": mock_pdf}
        response = self.random_client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        # Check that the correct template is used
        self.assertTemplateUsed(response, "library/lib_upload_doc.html")
        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], LibDocForm)
        self.assertFalse(response.context['form'].errors)

        # Check if lib doc saves shows that we reached this code block
        documents = LibDocuments.objects.filter(name=mock_file_name, user=LibraryTestCase.random_user)
        self.assertFalse(documents.exists())
        self.assertEqual(documents.count(), 0)

    @patch("library.views.upload_document_to_library")
    def test_upload_document_lib_embeddings_fail_random_user_save_successful_first_doc(self, chroma_upload_func):
        url = reverse("upload_document")
        pdf_content_test = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                            b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                            b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                            b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                            b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        mock_file_name = 'test_document_inside_test.pdf'

        mock_pdf = SimpleUploadedFile(
            name=mock_file_name,
            content=pdf_content_test,
            content_type='application/pdf'
        )
        end_id = 5
        chroma_upload_func.return_value = end_id
        post_data = {"upload_file": mock_pdf}
        response = self.random_client.post(url, post_data)

        self.assertEqual(response.status_code, 302)
        # Test redirect
        self.assertRedirects(response, reverse('lib_doc_list'))


        # Check if lib doc saves shows that we reached this code block
        documents = LibDocuments.objects.filter(name=mock_file_name, user=LibraryTestCase.random_user)
        self.assertTrue(documents.exists())
        self.assertEqual(documents.count(), 1)
        document = documents.first()

        file_path = os.path.join(settings.MEDIA_ROOT, document.upload_file.name)
        unique_user = f'user_{LibraryTestCase.random_user.id}'

        chroma_upload_func.assert_called_once_with(file_path=file_path, unique_user=unique_user, new_id=1)

        embeddings = LibDocumentEmbeddings.objects.get(document=document)
        self.assertEqual(embeddings.start_id, 1)
        self.assertEqual(embeddings.end_id, end_id)

    @patch("library.views.upload_document_to_library")
    def test_upload_document_lib_embeddings_fail_test_user_save_successful_not_first_doc(self, chroma_upload_func):
        url = reverse("upload_document")
        pdf_content_test = (b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 '
                            b'obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n'
                            b'<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref'
                            b'\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n'
                            b'\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF')

        mock_file_name = 'test_document_inside_test.pdf'

        mock_pdf = SimpleUploadedFile(
            name=mock_file_name,
            content=pdf_content_test,
            content_type='application/pdf'
        )
        expected_start_id = 342
        expected_end_id = 350
        chroma_upload_func.return_value = expected_end_id
        post_data = {"upload_file": mock_pdf}
        response = self.authenticated_client.post(url, post_data)

        self.assertEqual(response.status_code, 302)
        # Test redirect
        self.assertRedirects(response, reverse('lib_doc_list'))

        # Check if lib doc saves shows that we reached this code block
        documents = LibDocuments.objects.filter(name=mock_file_name, user=LibraryTestCase.test_user)
        self.assertTrue(documents.exists())
        self.assertEqual(documents.count(), 1)
        document = documents.first()

        file_path = os.path.join(settings.MEDIA_ROOT, document.upload_file.name)
        unique_user = f'user_{LibraryTestCase.test_user.id}'

        chroma_upload_func.assert_called_once_with(file_path=file_path, unique_user=unique_user,
                                                   new_id=expected_start_id)

        embeddings = LibDocumentEmbeddings.objects.get(document=document)
        self.assertEqual(embeddings.start_id, expected_start_id)
        self.assertEqual(embeddings.end_id, expected_end_id)

    @patch("library.views.delete_document_from_library")
    def test_lib_doc_delete_different_user(self, delete_chroma_func):

        pk = LibraryTestCase.document_2.pk

        url = reverse("delete_document", args=[pk])

        first_response = self.random_client.get(url)
        self.assertEqual(first_response.status_code, 404)
        delete_chroma_func.assert_not_called()

    @patch("library.views.delete_document_from_library")
    def test_lib_doc_delete_unauthenticated_user(self, delete_chroma_func):

        pk = LibraryTestCase.document_2.pk

        url = reverse("delete_document", args=[pk])

        first_response = self.unauthenticated_client.get(url)
        self.assertEqual(first_response.status_code, 404)
        delete_chroma_func.assert_not_called()

    @patch("library.views.delete_document_from_library")
    def test_lib_doc_delete_success(self, delete_chroma_func):

        before_docs = LibDocuments.objects.filter(user=LibraryTestCase.test_user)
        before_count = before_docs.count()
        self.assertEqual(before_count, 2)

        before_embeddings = LibDocumentEmbeddings.objects.filter(document__in=before_docs)
        self.assertEqual(before_embeddings.count(), 2)

        pk = LibraryTestCase.document_2.pk

        document_delete = LibDocuments.objects.filter(pk=pk)
        specific_document = document_delete.first()
        file_path = specific_document.upload_file.path
        document_embedding = LibDocumentEmbeddings.objects.filter(document=specific_document)
        unique_user = f'user_{LibraryTestCase.test_user.id}'

        self.assertTrue(document_delete.exists())
        self.assertTrue(document_embedding.exists())
        self.assertEqual(document_delete.count(), 1)
        self.assertEqual(document_embedding.count(), 1)


        url = reverse("delete_document", args=[pk])

        first_response = self.authenticated_client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, "library/confirm_doc_delete.html")

        second_response = self.authenticated_client.post(url)
        self.assertEqual(second_response.status_code, 302)
        redirect_url = reverse("lib_doc_list")
        self.assertEqual(second_response.url, redirect_url)

        document_delete = LibDocuments.objects.filter(pk=pk)
        document_embedding = LibDocumentEmbeddings.objects.filter(document=specific_document)
        self.assertFalse(document_delete.exists())
        self.assertFalse(document_embedding.exists())
        self.assertFalse(os.path.exists(file_path))
        delete_chroma_func.assert_called_once_with(number_of_documents=before_count,
                                                   document_pk=pk, unique_user=unique_user)


class UtilsTestCase(unittestTestCase):

    def test_get_final_id_success(self):
        output = get_final_id(num="id456")
        self.assertEqual(output, 456)

    def test_get_final_id_exception(self):
        output = get_final_id(num="idnonumber")
        self.assertFalse(output)

    def test_get_lists_for_chroma_upsert_new_id_one(self):

        document_1 = MockLangchainDocument(page_content="document_1", metadata="document_1")
        document_2 = MockLangchainDocument(page_content="document_2", metadata="document_2")
        document_3 = MockLangchainDocument(page_content="document_3", metadata="document_3")

        all_splits = [document_1, document_2, document_3]
        new_id = 1

        expected_id_list, expected_page_content_list, expected_metadata_list = get_lists_for_chroma_upsert(
            all_splits=all_splits, new_id=new_id)

        actual_id_list = []
        actual_page_content_list = []
        actual_metadata_list = []

        for split in all_splits:
            actual_id_list.append(f'id{new_id}')
            actual_page_content_list.append(split.page_content)
            actual_metadata_list.append(split.metadata)
            new_id += 1

        self.assertEqual(actual_id_list, expected_id_list)
        self.assertEqual(actual_page_content_list, expected_page_content_list)
        self.assertEqual(actual_metadata_list, expected_metadata_list)

    def test_get_lists_for_chroma_upsert_new_id_not_one(self):

        document_1 = MockLangchainDocument(page_content="document_1", metadata="document_1")
        document_2 = MockLangchainDocument(page_content="document_2", metadata="document_2")
        document_3 = MockLangchainDocument(page_content="document_3", metadata="document_3")

        all_splits = [document_1, document_2, document_3]
        new_id = 456

        expected_id_list, expected_page_content_list, expected_metadata_list = get_lists_for_chroma_upsert(
            all_splits=all_splits, new_id=new_id)

        actual_id_list = []
        actual_page_content_list = []
        actual_metadata_list = []

        for split in all_splits:
            actual_id_list.append(f'id{new_id}')
            actual_page_content_list.append(split.page_content)
            actual_metadata_list.append(split.metadata)
            new_id += 1

        self.assertEqual(actual_id_list, expected_id_list)
        self.assertEqual(actual_page_content_list, expected_page_content_list)
        self.assertEqual(actual_metadata_list, expected_metadata_list)

    def test_get_list_ids_chroma_deletion_start_id_one(self):

        start_id = 1
        end_id = 25

        expected_list_of_ids = get_list_of_ids_for_chroma_deletion(start_id=start_id, end_id=end_id)

        actual_list_of_ids = [f"id{i}" for i in range(start_id, end_id + 1)]

        self.assertEqual(actual_list_of_ids, expected_list_of_ids)

    def test_get_list_ids_chroma_deletion_start_id_not_one(self):

        start_id = 50
        end_id = 76

        expected_list_of_ids = get_list_of_ids_for_chroma_deletion(start_id=start_id, end_id=end_id)

        actual_list_of_ids = [f"id{i}" for i in range(start_id, end_id + 1)]

        self.assertEqual(actual_list_of_ids, expected_list_of_ids)

