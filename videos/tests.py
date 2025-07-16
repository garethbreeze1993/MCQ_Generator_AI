from django.test import TestCase, Client
from django.contrib.auth.models import User
from videos.models import Video
from videos.forms import VideoForm
import requests
from io import BytesIO
import json

from django.urls import reverse
from django.http import FileResponse
from django.conf import settings

from unittest.mock import patch


class ClientError(Exception):

    def __init__(self, value=None):
        self.value = value

    def response(self):
        if self.value:
            return {'Error': {'Code': 'NoSuchKey'}}
        else:
            return {'Error': {'Code': 'Somthing else'}}


class MockS3Client:

    def __init__(self, raise_exception=False, generic_exception=False, value=False):
        self.raise_exception = raise_exception
        self.generic_exception = generic_exception
        self.value = value

    presigned_url = "http://fakes3url.aws.com"

    def generate_presigned_url(self, action, Params, ExpiresIn):
        if self.raise_exception:
            raise Exception
        return MockS3Client.presigned_url

    def get_object(self, Bucket, Key):
        if self.raise_exception:
            if self.generic_exception:
                raise Exception
            else:
                if self.value:
                    raise ClientError(value=self.value)
                else:
                    raise ClientError

        return {
            'Body': BytesIO(b'test video content')
        }


class MockAPIResponse:

    def __init__(self, raise_exception=False):
        self.raise_exception = raise_exception

    mock_response = {"status": "processing", "message": "Still Processing"}

    def json(self):
        return self.mock_response

    def raise_for_status(self):
        if self.raise_exception:
            raise requests.RequestException
        return True


class VideoTestCase(TestCase):


    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password')
        cls.random_user = User.objects.create_user(username='randomuser', password='random')

        for i in range(1, 5):
            status_dict = {1: "completed", 2: "processing", 3: "error", 4: "uploaded"}
            if i < 4:
                celery_task_id = f"celery_task_id_{i}"
            else:
                celery_task_id = None

            if i == 1:
                s3_url = f"http://s3.url/videos/{i}.mp4"
            else:
                s3_url = None

            Video.objects.create(title=f"Video_title_{i}", prompt=f"Prompt_{i}", user=cls.test_user,
                                       status=status_dict[i], celery_task_id=celery_task_id, s_three_url=s3_url)

        for i in range(6, 10):
            status_dict = {6: "completed", 7: "processing", 8: "error", 9: "uploaded"}
            if i < 9:
                celery_task_id = f"celery_task_random_id_{i}"
            else:
                celery_task_id = None

            if i == 6:
                s3_url = f"http://s3.url/videos/{i}.mp4"
            else:
                s3_url = None

            Video.objects.create(title=f"Video_title_{i}", prompt=f"Prompt_{i}", user=cls.random_user,
                                       status=status_dict[i], celery_task_id=celery_task_id, s_three_url=s3_url)

    def setUp(self):
        # Every test needs a client.
        self.authenticated_client = Client()
        self.authenticated_client.login(username='testuser', password='password')
        self.unauthenticated_client = Client()
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')


    def test_authenticated_client_get_all_lib_chats_test_user(self):
        url = reverse("video_index")
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['videos']), 4)

        videos_queryset = Video.objects.filter(user=VideoTestCase.test_user)

        self.assertEqual(list(videos_queryset), list(response.context['videos']))
        self.assertTemplateUsed(response, "videos/video_index.html")

    def test_authenticated_client_get_all_lib_chats_random_user(self):
        url = reverse("video_index")
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['videos']), 4)

        videos_queryset = Video.objects.filter(user=VideoTestCase.random_user)

        self.assertEqual(list(videos_queryset), list(response.context['videos']))
        self.assertTemplateUsed(response, "videos/video_index.html")

    def test_unauthenticated_client_get_all_lib_chats(self):
        url = reverse("video_index")
        response = self.unauthenticated_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    @patch("videos.views.get_s3_client")
    def test_authenticated_client_get_video_detail_data_completed_no_errors(self, s3_client):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{1}").first()
        video_pk = video.pk
        fake_s3_client = MockS3Client()
        s3_client.return_value = fake_s3_client
        url = reverse("video_detail", args=[video_pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video'], video)
        self.assertEqual(response.context['video_url'], fake_s3_client.presigned_url)
        self.assertIsNone(response.context['status'])
        self.assertIsNone(response.context['message'])
        self.assertTemplateUsed(response, "videos/video_detail.html")

    def test_unauthenticated_client_get_video_detail_data(self):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{1}").first()
        video_pk = video.pk
        url = reverse("video_detail", args=[video_pk])
        response = self.unauthenticated_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_authenticated_client_get_video_detail_data_wrong_user(self):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{1}").first()
        video_pk = video.pk
        url = reverse("video_detail", args=[video_pk])
        response = self.random_client.get(url)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 404)

    @patch("videos.views.get_s3_client")
    def test_authenticated_client_get_video_detail_data_completed_errors_when_s3_client_got(self, s3_client):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{1}").first()
        video_pk = video.pk
        fake_s3_client = MockS3Client(raise_exception=True)
        s3_client.return_value = fake_s3_client
        url = reverse("video_detail", args=[video_pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video'], video)
        self.assertEqual(response.context['video_url_error'], "Could not load video.")
        self.assertIsNone(response.context['video_url'])
        self.assertIsNone(response.context['status'])
        self.assertIsNone(response.context['message'])
        self.assertTemplateUsed(response, "videos/video_detail.html")

    @patch("videos.views.get_s3_client")
    def test_authenticated_client_get_video_detail_data_completed_s3_client_none(self, s3_client):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{1}").first()
        video_pk = video.pk
        s3_client.return_value = None
        url = reverse("video_detail", args=[video_pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video'], video)
        self.assertEqual(response.context['video_url_error'], "Could not load video.")
        self.assertIsNone(response.context['video_url'])
        self.assertIsNone(response.context['status'])
        self.assertIsNone(response.context['message'])
        self.assertTemplateUsed(response, "videos/video_detail.html")

    @patch("videos.views.requests.get")
    def test_authenticated_client_get_video_detail_data_processing_no_errors(self, api_call):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{2}").first()
        video_pk = video.pk
        url = reverse("video_detail", args=[video_pk])
        mock_api_obj = MockAPIResponse()
        api_call.return_value = mock_api_obj
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video'], video)
        self.assertIsNone(response.context['video_url'])
        self.assertEqual(response.context['status'], mock_api_obj.mock_response["status"])
        self.assertEqual(response.context['message'], mock_api_obj.mock_response["message"])
        self.assertTemplateUsed(response, "videos/video_detail.html")

    @patch("videos.views.requests.get")
    def test_authenticated_client_get_video_detail_data_processing_errors(self, api_call):
        video = Video.objects.filter(user=VideoTestCase.test_user, title=f"Video_title_{2}").first()
        video_pk = video.pk
        url = reverse("video_detail", args=[video_pk])
        mock_api_obj = MockAPIResponse(raise_exception=True)
        api_call.return_value = mock_api_obj
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['video'], video)
        self.assertIsNone(response.context['video_url'])
        self.assertEqual(response.context['status'], "error")
        self.assertEqual(response.context['message'], f"Error connecting to API")
        self.assertTemplateUsed(response, "videos/video_detail.html")

    def test_authenticated_client_get_request_upload_video(self):
        url = reverse("create_video")
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "videos/upload_video.html")
        self.assertIsInstance(response.context['form'], VideoForm)

    def test_unauthenticated_client_get_request_upload_video(self):
        url = reverse("create_video")
        response = self.unauthenticated_client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch("videos.views.send_request_to_text_to_vid_api.delay_on_commit")
    def test_authenticated_client_post_request_upload_video_success(self, celery_task_pch):
        url = reverse("create_video")
        prompt = "Test prompt"
        title = "Test title for this test"
        response = self.authenticated_client.post(url, data={"title": title, "prompt": prompt})
        self.assertEqual(response.status_code, 302)
        videos = Video.objects.filter(user=VideoTestCase.test_user)
        self.assertEqual(videos.count(), 5)
        video = videos.filter(title=title).first()
        self.assertEqual(video.prompt, prompt)
        self.assertEqual(video.status, "processing")
        self.assertIsNone(video.celery_task_id)
        self.assertIsNone(video.s_three_url)
        celery_task_pch.assert_called_once()

    @patch("videos.views.send_request_to_text_to_vid_api.delay_on_commit")
    def test_authenticated_client_post_request_upload_video_form_not_valid(self, celery_task_pch):
        url = reverse("create_video")
        prompt = "Test prompt"
        title = f"Video_title_{1}"
        response = self.authenticated_client.post(url, data={"title": title, "prompt": prompt})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "videos/upload_video.html")
        celery_task_pch.assert_not_called()

    @patch("videos.views.send_request_to_text_to_vid_api.delay_on_commit")
    def test_unauthenticated_client_post_request_upload_video(self, celery_task_pch):
        url = reverse("create_video")
        prompt = "Test prompt"
        title = "Test title for this test"
        response = self.unauthenticated_client.post(url, data={"title": title, "prompt": prompt})
        self.assertEqual(response.status_code, 302)
        celery_task_pch.assert_not_called()

    @patch("videos.views.delete_s3_file.delay_on_commit")
    def test_lib_doc_delete_success_completed_vid(self, delete_video_func):
        pk = 1
        videos = Video.objects.filter(user=VideoTestCase.test_user)
        videos_count = videos.count()
        self.assertEqual(videos_count, 4)

        video = videos.filter(pk=pk)
        self.assertTrue(video.exists())

        url = reverse("delete_video", args=[pk])

        first_response = self.authenticated_client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, "videos/confirm_vid_delete.html")

        second_response = self.authenticated_client.post(url)
        self.assertEqual(second_response.status_code, 302)
        redirect_url = reverse("video_index")
        self.assertEqual(second_response.url, redirect_url)

        videos_after = Video.objects.filter(user=VideoTestCase.test_user)
        videos_after_count = videos_after.count()
        self.assertEqual(videos_after_count, 3)

        video_after = videos_after.filter(pk=pk)
        self.assertFalse(video_after.exists())

        delete_video_func.assert_called_with(video_id=pk)

    @patch("videos.views.delete_s3_file.delay_on_commit")
    def test_lib_doc_delete_success_not_completed_vid(self, delete_video_func):
        pk = 2
        videos = Video.objects.filter(user=VideoTestCase.test_user)
        videos_count = videos.count()
        self.assertEqual(videos_count, 4)

        video = videos.filter(pk=pk)
        self.assertTrue(video.exists())

        url = reverse("delete_video", args=[pk])

        first_response = self.authenticated_client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, "videos/confirm_vid_delete.html")

        second_response = self.authenticated_client.post(url)
        self.assertEqual(second_response.status_code, 302)
        redirect_url = reverse("video_index")
        self.assertEqual(second_response.url, redirect_url)

        videos_after = Video.objects.filter(user=VideoTestCase.test_user)
        videos_after_count = videos_after.count()
        self.assertEqual(videos_after_count, 3)

        video_after = videos_after.filter(pk=pk)
        self.assertFalse(video_after.exists())

        delete_video_func.assert_not_called()

    @patch("videos.views.delete_s3_file.delay_on_commit")
    def test_lib_doc_delete_wrong_user(self, delete_video_func):
        pk = 2
        videos = Video.objects.filter(user=VideoTestCase.test_user)
        videos_count = videos.count()
        self.assertEqual(videos_count, 4)

        video = videos.filter(pk=pk)
        self.assertTrue(video.exists())

        url = reverse("delete_video", args=[pk])

        first_response = self.random_client.get(url)
        self.assertEqual(first_response.status_code, 404)
        delete_video_func.assert_not_called()

    @patch("videos.views.delete_s3_file.delay_on_commit")
    def test_lib_doc_delete_unauthenticated_user(self, delete_video_func):
        pk = 2
        videos = Video.objects.filter(user=VideoTestCase.test_user)
        videos_count = videos.count()
        self.assertEqual(videos_count, 4)

        video = videos.filter(pk=pk)
        self.assertTrue(video.exists())

        url = reverse("delete_video", args=[pk])

        first_response = self.unauthenticated_client.get(url)
        self.assertEqual(first_response.status_code, 404)
        delete_video_func.assert_not_called()

    @patch('videos.views.get_s3_client')
    def test_download_video_success(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client()
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{pk}.mp4"')
        self.assertEqual(response.getvalue(), b'test video content')

    @patch('videos.views.get_s3_client')
    def test_download_video_raise_generic_exception(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client(raise_exception=True, generic_exception=True)
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
        redirect_url = reverse("video_detail", args=[pk])
        self.assertEqual(response.url, redirect_url)

    @patch('videos.views.get_s3_client')
    def test_download_video_raise_exception_nosuchkey(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client(raise_exception=True, generic_exception=False, value=True)
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
        redirect_url = reverse("video_detail", args=[pk])
        self.assertEqual(response.url, redirect_url)

    @patch('videos.views.get_s3_client')
    def test_download_video_raise_exception_other(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client(raise_exception=True, generic_exception=False)
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
        redirect_url = reverse("video_detail", args=[pk])
        self.assertEqual(response.url, redirect_url)

    @patch('videos.views.get_s3_client')
    def test_download_video_s3_client_none(self, mock_get_s3_client):
        mock_get_s3_client.return_value = None
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.authenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
        redirect_url = reverse("video_detail", args=[pk])
        self.assertEqual(response.url, redirect_url)

    @patch('videos.views.get_s3_client')
    def test_download_video_wrong_user(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client()
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.random_client.get(url)
        self.assertEqual(response.status_code, 404)
        mock_get_s3_client.assert_not_called()

    @patch('videos.views.get_s3_client')
    def test_download_video_unauthenticated_user(self, mock_get_s3_client):
        mock_get_s3_client.return_value = MockS3Client()
        pk = 1
        url = reverse("download_video", args=[pk])
        response = self.unauthenticated_client.get(url)
        self.assertEqual(response.status_code, 302)
        mock_get_s3_client.assert_not_called()

    def test_video_complete_notification_success(self):

        payload = {'video_id': 2, 'job_id': 'ce7744f9-a0ad-4339-bbcc-0cadfd79b26543', 'status': 'completed',
                   'completed_at': '2025-06-26T17:59:07.389738', 'video_url': 'http://fakes3url.aws.com',
                   'error_message': ""}

        headers = {"Authorization": f"Bearer {settings.DJANGO_API_KEY}"}

        url = reverse("video_complete_notification")

        response = self.authenticated_client.post(url, data=payload, headers=headers, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['message'], "Webhook processed")

        video = Video.objects.get(pk=payload['video_id'])

        self.assertEqual(video.status, "completed")
        self.assertEqual(video.s_three_url, payload['video_url'])

    def test_video_complete_notification_some_fields_not_in_payload(self):

        payload = {'video_id': 2, 'job_id': 'ce7744f9-a0ad-4339-bbcc-0cadfd79b26543', 'status': 'completed',
                   'completed_at': '2025-06-26T17:59:07.389738', 'video_url': 'http://fakes3url.aws.com'}

        headers = {"Authorization": f"Bearer {settings.DJANGO_API_KEY}"}

        url = reverse("video_complete_notification")

        response = self.authenticated_client.post(url, data=payload, headers=headers, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Missing fields")

    def test_video_complete_invalid_json(self):

        payload = b"{invalid_json",

        headers = {"Authorization": f"Bearer {settings.DJANGO_API_KEY}"}

        url = reverse("video_complete_notification")

        response = self.client.generic(
            method='POST',
            path=url,
            data=payload,  # malformed bytes
            content_type='application/json',
            headers=headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Invalid JSON")

    def test_video_complete_notification_wrong_api_key(self):

        payload = {'video_id': 2, 'job_id': 'ce7744f9-a0ad-4339-bbcc-0cadfd79b26543', 'status': 'completed',
                   'completed_at': '2025-06-26T17:59:07.389738', 'video_url': 'http://fakes3url.aws.com',
                   'error_message': ""}

        headers = {"Authorization": f"Bearer random_api_key"}

        url = reverse("video_complete_notification")

        response = self.authenticated_client.post(url, data=payload, headers=headers, content_type='application/json')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Unauthorized")

    def test_video_complete_notification_no_api_key(self):

        payload = {'video_id': 2, 'job_id': 'ce7744f9-a0ad-4339-bbcc-0cadfd79b26543', 'status': 'completed',
                   'completed_at': '2025-06-26T17:59:07.389738', 'video_url': 'http://fakes3url.aws.com',
                   'error_message': ""}

        headers = {}

        url = reverse("video_complete_notification")

        response = self.authenticated_client.post(url, data=payload, headers=headers, content_type='application/json')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Unauthorized")
