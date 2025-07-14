from django.test import TestCase, Client
from django.contrib.auth.models import User
from videos.models import Video
from videos.forms import VideoForm
import requests

from django.urls import reverse

from unittest.mock import patch

class MockS3Client:

    def __init__(self, raise_exception=False):
        self.raise_exception = raise_exception

    presigned_url = "http://fakes3url.aws.com"

    def generate_presigned_url(self, action, Params, ExpiresIn):
        if self.raise_exception:
            raise Exception
        return MockS3Client.presigned_url


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
