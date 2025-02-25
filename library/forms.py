from django.forms import ModelForm
from django.core.validators import FileExtensionValidator

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

