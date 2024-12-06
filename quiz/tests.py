from io import BytesIO
import json
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, Client
from django.contrib.auth.models import User

from quiz.models import Quiz, Question, Answer
from quiz.forms import QuizForm



example_response_json = """{
  "quiz_name": "Example Quiz Name",
  "items":
[
{"question":  "What is the capital of France?",
  "answers": ["London", "Paris", "New York", "Toulouse"],
  "question_number": 1,
  "correct_answer": "Paris"
},
  {
      "question": "What is the official currency of Germany",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Euro",
    "question_number": 2
  }
]
}"""

new_quiz_request_json = """
[
{"question":  "What is the capital of England?",
  "answers": ["London", "Paris", "New York", "Toulouse"],
  "question_number": 1,
  "correct_answer": "London"
},
  {
      "question": "What is the official currency of the United States?",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Dollar",
    "question_number": 2
  }
]
"""

error_question_request_json = """
[
{"question":  "What is the capital of England?",
  "answers": ["London", "Paris", "New York", "Toulouse"],
  "question_number": "not a number",
  "correct_answer": "London"
},
  {
      "question": "What is the official currency of the United States?",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Dollar",
    "question_number": 2
  }
]
"""

error_answer_request_json = """
[
{"question":  "What is the capital of England?",
  "answers": ["London", "Paris", "New York", "Toulouse", 5],
  "question_number": 1,
  "correct_answer": "London"
},
  {
      "question": "What is the official currency of the United States?",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Dollar",
    "question_number": 2
  }
]
"""

error_request_json = """
[[
{"question":  "What is the capital of England?",
  "answers": ["London", "Paris", "New York", "Toulouse"],
  "question_number": 1,
  "correct_answer": "London"
},
  {
      "question": "What is the official currency of the United States?",
      "answers": ["Euro", "Dollar", "Deutschmark", "Pound"
      ],
      "correct_answer": "Dollar",
    "question_number": 2
  }
]
"""


class QuizTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='testuser', password='password')

        cls.random_user = User.objects.create_user(username='randomuser', password='random')
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

    def test_authenticated_client_get_quiz_detail_data(self):
        pk = QuizTestCase.test_quiz.pk
        # Get the questions associated with this quiz
        questions = Question.objects.filter(quiz=QuizTestCase.test_quiz).order_by('question_number')

        # For each question, get its answers
        quiz_data = []
        for question in questions:
            answers = Answer.objects.filter(question=question).order_by('answer_number')
            quiz_data.append({
                'question': question,
                'answers': answers
            })

        response = self.authenticated_client.get(f'/quiz/{pk}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['quiz'], QuizTestCase.test_quiz)
        self.assertEqual(len(response.context['quiz_data']), len(quiz_data))

        for index, data in enumerate(quiz_data):
            self.assertEqual(response.context['quiz_data'][index]['question'], quiz_data[index]['question'])
            # Change into list for answers as problems with equality operations on queryset
            self.assertEqual(
                list(response.context['quiz_data'][index]['answers']), list(quiz_data[index]['answers']))

    def test_random_authenticated_client_get_quiz_detail_fail(self):
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')
        pk = QuizTestCase.test_quiz.pk
        response = self.random_client.get(f'/quiz/{pk}')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode('utf-8'), "You are not allowed to access this quiz.")

    def test_unauthenticated_client_get_quiz_detail_data(self):
        pk = QuizTestCase.test_quiz.pk
        response = self.unauthenticated_client.get(f'/quiz/{pk}')
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    def test_create_form_get_request(self):
        # Simulate a GET request to the view
        response = self.authenticated_client.get('/quiz/create')

        # Check that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, "quiz/create_quiz.html")

        # Check that the form is in the context
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], QuizForm)

    def test_create_form_post_request_returns_forbidden(self):
        # Simulate a POST request to the view
        response = self.authenticated_client.post('/quiz/create')

        # Check that the response status code is 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

        # Check the response content
        self.assertEqual(response.content.decode(), 'DONT HIT THIS')

    def test_unauthenticated_client_create_form(self):
        response = self.unauthenticated_client.get('/quiz/create')
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain")
    def test_generate_quiz_file_txt_success_response_quiz_name_different(self, txt_langchain, pdf_langchain):
        # Create a mock file
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"

        txt_langchain.return_value = json.loads(example_response_json)

        post_data = {"file": mock_file, "quiz_name": "Example Quiz Name Forced", "number_of_questions": 9}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['items'],
                         json.loads(example_response_json)['items'])
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['quiz_name'],
                         post_data['quiz_name'])

        self.assertTrue(txt_langchain.called)

        self.assertFalse(pdf_langchain.called)

        txt_langchain_call_kwargs = txt_langchain.call_args[1]  # Get the kwargs from the call

        # Assert other arguments
        self.assertEqual(txt_langchain_call_kwargs["number_of_questions"], post_data["number_of_questions"])
        self.assertEqual(txt_langchain_call_kwargs["quiz_name"], post_data["quiz_name"])
        self.assertEqual(txt_langchain_call_kwargs["file"].name, "test_file.txt")

    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain")
    def test_generate_quiz_file_txt_success_response_quiz_name_not_different(self, txt_langchain, pdf_langchain):
        # Create a mock file
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"

        txt_langchain.return_value = json.loads(example_response_json)

        post_data = {"file": mock_file, "quiz_name": "Example Quiz Name", "number_of_questions": 9}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), json.loads(example_response_json))


        self.assertTrue(txt_langchain.called)

        self.assertFalse(pdf_langchain.called)

        txt_langchain_call_kwargs = txt_langchain.call_args[1]  # Get the kwargs from the call

        # Assert other arguments
        self.assertEqual(txt_langchain_call_kwargs["number_of_questions"], post_data["number_of_questions"])
        self.assertEqual(txt_langchain_call_kwargs["quiz_name"], post_data["quiz_name"])
        self.assertEqual(txt_langchain_call_kwargs["file"].name, "test_file.txt")


    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain")
    def test_generate_quiz_file_pdf_success_response(self, txt_langchain, pdf_langchain):
        # Create a mock file
        file_content = b"%PDF-1.4\n%Test PDF Content"

        pdf_file = BytesIO(file_content)
        pdf_file.name = "test.pdf"  # Name the file

        pdf_langchain.return_value = json.loads(example_response_json)

        post_data = {"file": pdf_file, "quiz_name": "Example Quiz Name", "number_of_questions": 9}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8')), json.loads(example_response_json))

        self.assertTrue(pdf_langchain.called)

        self.assertFalse(txt_langchain.called)

        pdf_langchain_call_kwargs = pdf_langchain.call_args[1]  # Get the kwargs from the call

        # Assert other arguments
        self.assertEqual(pdf_langchain_call_kwargs["number_of_questions"], post_data["number_of_questions"])
        self.assertEqual(pdf_langchain_call_kwargs["quiz_name"], post_data["quiz_name"])
        self.assertEqual(pdf_langchain_call_kwargs["file"].name, "test.pdf")

    def test_unauthenticated_client_generate_quiz(self):
        response = self.unauthenticated_client.get('/quiz/generate')
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)

    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain")
    def test_generate_quiz_file_txt_form_not_valid_number_of_questions_missing(self, txt_langchain, pdf_langchain):
        # Create a mock file
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"

        txt_langchain.return_value = json.loads(example_response_json)

        post_data = {"file": mock_file, "quiz_name": "Example Quiz Name"}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        form_errors_dict = json.loads(str(response.content, 'utf-8'))['form_errors']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Validation error")
        self.assertIsInstance(form_errors_dict, dict)
        self.assertTrue(form_errors_dict)

        for k, v in form_errors_dict.items():
            self.assertIsInstance(v, list)
            self.assertTrue(v)

    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain", side_effect=Exception)
    def test_generate_quiz_file_txt_llm_prompt_langchain_function_raises_exception(self, txt_langchain, pdf_langchain):
        # Create a mock file
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"

        post_data = {"file": mock_file, "quiz_name": "Example Quiz Name", "number_of_questions": 9}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        self.assertEqual(response.status_code, 500)
        self.assertTrue(txt_langchain.called)
        self.assertFalse(pdf_langchain.called)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'],"Error from llm integration")

    @patch("quiz.views.execute_llm_prompt_pdf")
    @patch("quiz.views.execute_llm_prompt_langchain")
    def test_generate_quiz_file_txt_llm_prompt_langchain_successful_type_error_raises_on_json_response(
            self, txt_langchain, pdf_langchain):

        # Create a mock file
        file_content = b"Hello, this is a test file"
        mock_file = BytesIO(file_content)
        mock_file.name = "test_file.txt"

        txt_langchain.return_value = example_response_json

        post_data = {"file": mock_file, "quiz_name": "Example Quiz Name", "number_of_questions": 9}

        response = self.authenticated_client.post('/quiz/generate', post_data)

        self.assertEqual(response.status_code, 500)
        self.assertTrue(txt_langchain.called)
        self.assertFalse(pdf_langchain.called)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'],
                         "Error when trying to make a JSONResponse.")


    def test_generate_quiz_get_request_returns_forbidden(self):
        # Simulate a POST request to the view
        response = self.authenticated_client.get('/quiz/generate')

        # Check that the response status code is 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

        # Check the response content
        self.assertEqual(response.content.decode(), 'DONT HIT THIS')

    def test_authenticated_client_delete_quiz_success(self):
        pk = QuizTestCase.test_quiz.pk
        quiz = Quiz.objects.filter(pk=pk)
        quiz_count = quiz.count()
        questions = Question.objects.filter(quiz_id=pk)
        questions_count = questions.count()
        answers_count = Answer.objects.filter(question__in=questions).count()
        self.assertEqual(quiz_count, 1)
        self.assertEqual(questions_count, 3)
        self.assertEqual(answers_count, 12)
        # Get the questions associated with this quiz
        response = self.authenticated_client.get(f'/quiz/delete/{pk}')


        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "quiz/confirm_delete.html")

        second_response = self.authenticated_client.post(f'/quiz/delete/{pk}')

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(second_response.url, '/quiz/')

        after_resp_quiz = Quiz.objects.filter(pk=pk)
        after_resp_quiz_count = after_resp_quiz.count()
        after_resp_questions = Question.objects.filter(quiz_id=pk)
        after_resp_questions_count = after_resp_questions.count()
        after_resp_answers_count = Answer.objects.filter(question__in=questions).count()


        self.assertEqual(after_resp_quiz_count, 0)
        self.assertEqual(after_resp_questions_count, 0)
        self.assertEqual(after_resp_answers_count, 0)

        third_response = self.authenticated_client.get(f'/quiz/')
        self.assertEqual(third_response.status_code, 200)
        self.assertEqual(len(third_response.context['quizzes']), 0)

    def test_random_authenticated_client_delete_quiz_fail(self):
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')
        pk = QuizTestCase.test_quiz.pk
        response = self.random_client.get(f'/quiz/delete/{pk}')

        self.assertEqual(response.status_code, 404)

        second_response = self.random_client.post(f'/quiz/delete/{pk}')
        self.assertEqual(second_response.status_code, 404)

    def test_random_authenticated_client_delete_quiz_fail_only_post_request(self):
        self.random_client = Client()
        self.random_client.login(username='randomuser', password='random')
        pk = QuizTestCase.test_quiz.pk
        post_response = self.random_client.post(f'/quiz/delete/{pk}')
        self.assertEqual(post_response.status_code, 404)


    def test_unauthenticated_client_delete_quiz(self):
        pk = QuizTestCase.test_quiz.pk
        response = self.unauthenticated_client.get(f'/quiz/delete/{pk}')
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 404)

    def test_save_method_success_response(self):

        post_data = {"whole_quiz": new_quiz_request_json, "quiz_name_user": "New Test Quiz Name"}
        quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(quiz_queryset.exists())
        response = self.authenticated_client.post('/quiz/save', post_data)
        self.assertEqual(response.status_code, 302)
        new_quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertTrue(new_quiz_queryset.exists())
        self.assertEqual(new_quiz_queryset.count(), 1)
        new_quiz_obj = new_quiz_queryset.first()
        questions_queryset = Question.objects.filter(quiz=new_quiz_obj).order_by('question_number')
        self.assertEqual(questions_queryset.count(), 2)
        self.assertEqual(questions_queryset[0].question_text, "What is the capital of England?")
        self.assertEqual(questions_queryset[1].question_text,
                         "What is the official currency of the United States?")

        answers_one_queryset = Answer.objects.filter(question=questions_queryset[0]).order_by('answer_number')
        answers_two_queryset = Answer.objects.filter(question=questions_queryset[1]).order_by('answer_number')

        self.assertEqual(answers_one_queryset.count(), 4)
        self.assertEqual(answers_two_queryset.count(), 4)

        answers_list = ["London", "Paris", "New York", "Toulouse"]

        for index, answer in enumerate(answers_one_queryset):
            self.assertEqual(answer.answer_number, index + 1)
            self.assertEqual(answers_one_queryset[index].answer_text, answers_list[index])

            if answer.answer_text == 'London':
                self.assertTrue(answer.correct)
            else:
                self.assertFalse(answer.correct)

        answer_list_2 = ["Euro", "Dollar", "Deutschmark", "Pound"]

        for index, answer_2 in enumerate(answers_two_queryset):

            self.assertEqual(answer_2.answer_number, index + 1)
            self.assertEqual(answers_two_queryset[index].answer_text, answer_list_2[index])

            if answer_2.answer_text == 'Dollar':
                self.assertTrue(answer_2.correct)
            else:
                self.assertFalse(answer_2.correct)

    def test_save_method_invalid_json_error(self):
        post_data = {"whole_quiz": error_request_json, "quiz_name_user": "New Test Quiz Name"}
        quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(quiz_queryset.exists())
        response = self.authenticated_client.post('/quiz/save', post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Invalid JSON")

    def test_save_method_error_saving_quiz(self):
        post_data = {"whole_quiz": new_quiz_request_json, "quiz_name_user": QuizTestCase.test_quiz.title}

        quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(quiz_queryset.exists())

        quiz_user_queryset_count = Quiz.objects.filter(user=QuizTestCase.test_user).count()
        self.assertEqual(quiz_user_queryset_count, 1)

        response = self.authenticated_client.post('/quiz/save', post_data)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Error when saving quiz")

        new_quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(new_quiz_queryset.exists())
        self.assertEqual(new_quiz_queryset.count(), 0)

        new_quiz_user_queryset_count = Quiz.objects.filter(user=QuizTestCase.test_user).count()
        self.assertEqual(new_quiz_user_queryset_count, 1)

    def test_save_method_error_saving_question(self):
        post_data = {"whole_quiz": error_question_request_json, "quiz_name_user": "New Test Quiz Name"}

        quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(quiz_queryset.exists())

        quiz_user_queryset_count = Quiz.objects.filter(user=QuizTestCase.test_user).count()
        self.assertEqual(quiz_user_queryset_count, 1)

        response = self.authenticated_client.post('/quiz/save', post_data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(str(response.content, 'utf-8'))['error'], "Error when saving question")

        new_quiz_queryset = Quiz.objects.filter(title="New Test Quiz Name", user=QuizTestCase.test_user)
        self.assertFalse(new_quiz_queryset.exists())
        self.assertEqual(new_quiz_queryset.count(), 0)

        new_quiz_user_queryset_count = Quiz.objects.filter(user=QuizTestCase.test_user).count()
        self.assertEqual(new_quiz_user_queryset_count, 1)

    # Unable to test failing an answer as unsure of how to do this in a unit test

    def test_unauthenticated_client_save_quiz(self):
        post_data = {"whole_quiz": error_question_request_json, "quiz_name_user": "New Test Quiz Name"}
        response = self.unauthenticated_client.post(f'/quiz/save', post_data)
        # Client not logged in so will do a redirect
        self.assertEqual(response.status_code, 302)
