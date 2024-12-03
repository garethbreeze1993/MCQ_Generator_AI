from django.test import TestCase, Client
from django.contrib.auth.models import User

from quiz.models import Quiz, Question, Answer


class QuizTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password')
        # cls.test_user = User.objects.get(username='testuser')
        cls.test_quiz = Quiz.objects.create(title='test title', user=cls.test_user)
        # test_quiz = Quiz.objects.get(title='test title')
        for i in range(1, 4):
            q = Question.objects.create(question_text=f'test_question_{i}', question_number=i, quiz=cls.test_quiz)
            setattr(cls, f'question_{i}', q)


        cls.question_one = getattr(cls, 'question_1')
        cls.question_two = getattr(cls, 'question_2')
        cls.question_three = getattr(cls, 'question_3')

        for i in range(1, 5):
            a_one = Answer.objects.create(answer_text=f'test_answer_{i}', answer_number=i, question=cls.question_one,
                                  correct=i == 1)
            setattr(cls, f'question_1_answer_{i}', a_one)
            a_two = Answer.objects.create(answer_text=f'test_answer_{i}', answer_number=i, question=cls.question_two,
                                  correct=i == 2)
            setattr(cls, f'question_2_answer_{i}', a_two)
            a_three = Answer.objects.create(answer_text=f'test_answer_{i}', answer_number=i, question=cls.question_three,
                                  correct=i == 3)
            setattr(cls, f'question_3_answer_{i}', a_three)

    def setUp(self):
        # Every test needs a client.
        self.authenticated_client = Client()
        self.authenticated_client.login(username='testuser', password='password')
        self.unauthenticated_client = Client()


    def test_authenticated_client_get_quiz(self):
        response = self.authenticated_client.get('/quiz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['quizzes']), 1)
        self.assertEqual(response.context['quizzes'][0], QuizTestCase.test_quiz)

    def test_unauthenticated_client_get_quiz(self):
        response = self.unauthenticated_client.get('/quiz/')
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

