import os
import json
import logging


from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from .forms import QuizForm
from .models import Quiz, Question, Answer
from .llm_integration import execute_llm_prompt_langchain, execute_llm_prompt_pdf
from .utils import handle_uploaded_file
from django.http import HttpResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

logger = logging.getLogger("django_mcq")



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

    logger.debug("testing output")
    logger.debug(pk)
    # Get the quiz by pk or return 404 if not found
    quiz = get_object_or_404(Quiz, pk=pk)

    # Check if the logged-in user is associated with the quiz
    if quiz.user != request.user:
        return HttpResponseForbidden("You are not allowed to access this quiz.")

    logger.debug(quiz)

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

    else:
        return HttpResponseForbidden('DONT HIT THIS')

    return render(request, "quiz/create_quiz.html", {"form": form})
@login_required(login_url='login')
def generate_quiz(request):

    if request.method == 'POST':
        form = QuizForm(request.POST, request.FILES)

        if form.is_valid():

            name_of_file = request.FILES['file'].name

            if name_of_file.endswith('.pdf'):
                pdf = True
            else:
                # file is .txt
                pdf = False


            try:
                if not pdf:
                    llm_quiz_data = execute_llm_prompt_langchain(number_of_questions=form.cleaned_data['number_of_questions'],
                                                                 quiz_name=form.cleaned_data['quiz_name'],
                                                                 file=form.cleaned_data['file'])
                else:
                    llm_quiz_data = execute_llm_prompt_pdf(number_of_questions=form.cleaned_data['number_of_questions'],
                                                                 quiz_name=form.cleaned_data['quiz_name'],
                                                                 file=form.cleaned_data['file'])
            except Exception as e:
                logger.error(e)
                return JsonResponse({"error": "Error from llm integration"}, status=500)

            try:

                if not pdf:
                    # Force it to have quiz name of user input
                    llm_quiz_data['quiz_name'] = form.cleaned_data['quiz_name']

                success_response = JsonResponse(llm_quiz_data)

            except TypeError as e:
                logger.error(e)
                return JsonResponse({"error": "Error when trying to make a JSONResponse."}, status=500)

            else:
                return success_response
        else:
            form_errors_dict = dict(form.errors)
            return JsonResponse({"error": "Validation error", "form_errors": form_errors_dict}, status=200)

    else:
        return HttpResponseForbidden('DONT HIT THIS')


@login_required(login_url='login')
def save_quiz(request):
    whole_quiz = request.POST['whole_quiz']
    whole_quiz_qs = json.loads(whole_quiz)

    logger.debug(whole_quiz_qs)

    new_quiz = Quiz()
    new_quiz.user = request.user
    new_quiz.title = request.POST['quiz_name_user']
    new_quiz.save()

    for question in whole_quiz_qs:
        new_question = Question()
        new_question.quiz = new_quiz
        new_question.question_text = question.get('question')
        new_question.question_number = question.get('question_number')

        new_question.save()

        for answer_key, answer_value in enumerate(question['answers']):

            new_answer = Answer()
            new_answer.question = new_question
            new_answer.answer_text = answer_value
            new_answer.answer_number = answer_key + 1

            if answer_value == question['correct_answer']:
                new_answer.correct = True
            else:
                new_answer.correct = False

            new_answer.save()

    return redirect("index")


class QuizDeleteView(DeleteView):
    # specify the model you want to use
    model = Quiz

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_url = reverse_lazy("index")

    template_name = "quiz/confirm_delete.html"

