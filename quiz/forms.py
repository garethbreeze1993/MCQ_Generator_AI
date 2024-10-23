from django import forms


class QuizForm(forms.Form):
    quiz_name = forms.CharField(label="Quiz Name", max_length=128)
    file = forms.FileField()
    number_of_questions = forms.IntegerField(label="Number of Questions", min_value=1, max_value=10)
    temperature = forms.IntegerField(label="Temperature", min_value=0, max_value=2)