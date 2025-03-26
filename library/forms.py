from django.forms import ModelForm
from django.core.validators import FileExtensionValidator

from library.models import LibDocuments

from django import forms
from library.models import LibDocuments

class LibDocForm(ModelForm):

    class Meta:
        model = LibDocuments

        fields = ["upload_file"]

    def clean_upload_file(self):
        file = self.cleaned_data.get("upload_file")
        if file:
            validator = FileExtensionValidator(allowed_extensions=["pdf"])
            validator(file)
        return file

class LibChatTitleForm(forms.Form):
    name_title = forms.CharField(label="Chat Name", max_length=128)
    document = forms.ModelMultipleChoiceField(
        queryset=LibDocuments.objects.none(),  # We'll set this dynamically
        label="Choose a document",
        widget=forms.SelectMultiple(attrs={"class": "form-control"})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].queryset = LibDocuments.objects.filter(user=user, status="completed")

class SaveLibChatTitleForm(forms.Form):
    name_title = forms.CharField(label="Chat Name", max_length=128)



