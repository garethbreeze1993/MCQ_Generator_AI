from django.test import TestCase, Client
from django.contrib.auth.models import User
from videos.models import Video

from django.urls import reverse


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


