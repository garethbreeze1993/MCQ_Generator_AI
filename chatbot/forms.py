from django import forms

class ChatTitleForm(forms.Form):
    name_title = forms.CharField(label="Chat Name", max_length=128)