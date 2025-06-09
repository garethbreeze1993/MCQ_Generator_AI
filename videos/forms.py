from django.forms import ModelForm, Textarea

from videos.models import Video

class VideoForm(ModelForm):

    class Meta:
        model = Video

        fields = ["title", "prompt"]

        widgets = {
            "prompt": Textarea(attrs={
                "rows": 5,
                "cols": 40,
                "placeholder": "Enter your prompt here..."
            }),
        }