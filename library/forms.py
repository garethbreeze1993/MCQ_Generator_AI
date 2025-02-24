from django import forms
from django.core.validators import FileExtensionValidator

class LibDocForm(forms.Form):
    file = forms.FileField(validators=[FileExtensionValidator( ['txt', 'pdf'] ) ])