from django.urls import path

from .views import SignUpView, activate_account, user_login

from accounts.forms import EmailAuthenticationForm

from django.views.generic import TemplateView

from django.contrib.auth.views import LoginView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("activate/<uidb64>/<token>/", activate_account, name="activate"),
    path("account-activation-sent/", TemplateView.as_view(
        template_name="registration/account_activation_sent.html"), name="account_activation_sent"),
]