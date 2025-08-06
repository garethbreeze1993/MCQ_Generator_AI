# main/forms.py
from django import forms

class ContactForm(forms.Form):
    email = forms.EmailField(label='Your email')
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)
