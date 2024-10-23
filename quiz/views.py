import os
import json

from django.conf import settings
from django.shortcuts import render
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

                return JsonResponse(data)

            except FileNotFoundError:
                return JsonResponse({"error": "File not found."}, status=404)

            except json.JSONDecodeError:
                return JsonResponse({"error": "Error decoding JSON."}, status=500)
    else:
        return HttpResponseForbidden('DONT HIT THIS')

