from django.urls import path

from .views import SignUpView, activate_account, ResendActivationEmailView

from accounts.forms import CustomAuthenticationForm

from django.views.generic import TemplateView

from django.contrib.auth.views import LoginView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("activate/<uidb64>/<token>/", activate_account, name="activate"),
    path("account-activation-sent/", TemplateView.as_view(
        template_name="registration/account_activation_sent.html"), name="account_activation_sent"),
    path("login/", LoginView.as_view(
            authentication_form=CustomAuthenticationForm,
            template_name="registration/login.html"
        ), name="login"),
    path("resend_activation", ResendActivationEmailView.as_view(), name="resend_activation")
]