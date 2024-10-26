import os
import json

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from .forms import QuizForm
from .models import Quiz, Question, Answer
from .utils import handle_uploaded_file
from django.http import HttpResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required


class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    paginate_by = 10  # if pagination is desired
    template_name = 'quiz/index.html'  # Specify your template name
    context_object_name = 'quizzes'  # The variable to use in the template

    def get_queryset(self):
        # Filter quizzes by the current logged-in user
        return Quiz.objects.filter(user=self.request.user)

@login_required(login_url='login')
def get_quiz_data(request, pk):
    # Get the quiz by pk or return 404 if not found
    quiz = get_object_or_404(Quiz, pk=pk)

    # Check if the logged-in user is associated with the quiz
    if quiz.user != request.user:
        return HttpResponseForbidden("You are not allowed to access this quiz.")

    # Get the questions associated with this quiz
    questions = Question.objects.filter(quiz=quiz).order_by('question_number')

    # For each question, get its answers
    quiz_data = []
    for question in questions:
        answers = Answer.objects.filter(question=question).order_by('answer_number')
        quiz_data.append({
            'question': question,
            'answers': answers
        })

    # Send the structured data to the template
    context = {
        'quiz': quiz,
        'quiz_data': quiz_data
    }

    return render(request, 'quiz/quiz_detail.html', context)
@login_required(login_url='login')
def create_quiz(request):

    form = None

    if request.method == 'GET':
        form = QuizForm()

    elif request.method == 'POST':
        pass

    else:
        return HttpResponseForbidden('DONT HIT THIS')

    return render(request, "quiz/create_quiz.html", {"form": form})
@login_required(login_url='login')
def generate_quiz(request):

    if request.method == 'POST':
        form = QuizForm(request.POST, request.FILES)
        if form.is_valid():
            json_file_path = os.path.join(settings.BASE_DIR, 'quiz', 'static', 'response.json')

            # Open and read the JSON file
            try:
                with open(json_file_path, 'r') as json_file:
                    data = json.load(json_file)
                    data['quiz_name'] = request.POST['quiz_name']

                return JsonResponse(data)

            except FileNotFoundError:
                return JsonResponse({"error": "File not found."}, status=404)

            except json.JSONDecodeError:
                return JsonResponse({"error": "Error decoding JSON."}, status=500)
    else:
        return HttpResponseForbidden('DONT HIT THIS')


@login_required(login_url='login')
def save_quiz(request):
    whole_quiz = request.POST['whole_quiz']
    whole_quiz_qs = json.loads(whole_quiz)

    new_quiz = Quiz()
    new_quiz.user = request.user
    new_quiz.title = request.POST['quiz_name_user']
    new_quiz.save()

    for question in whole_quiz_qs:
        question_key = list(question.keys())
        question_number = question_key[0]
        question_value = question[question_number]
        new_question = Question()
        new_question.quiz = new_quiz
        new_question.question_text = question_value.get('question')
        new_question.question_number = question_number

        new_question.save()

        for answer_key, answer_value in question_value['answers'].items():

            new_answer = Answer()
            new_answer.question = new_question
            new_answer.answer_text = answer_value
            new_answer.answer_number = answer_key

            if int(answer_key) == int(question_value['correct_answer']):
                new_answer.correct = True
            else:
                new_answer.correct = False

            new_answer.save()

    return redirect("index")
