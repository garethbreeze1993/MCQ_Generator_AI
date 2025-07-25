from django import forms
from django.contrib.auth.forms import UserCreationForm
# from accounts.models import CustomUser
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):

    username = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autofocus": True, 'placeholder': 'Enter your email'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Email"

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.", code='inactive')
