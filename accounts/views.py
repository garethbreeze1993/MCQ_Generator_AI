# accounts/views.py
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from accounts.forms import SignUpForm, ResendActivationEmailForm
from django.contrib.auth import authenticate, login
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.generic import FormView

from accounts.tokens import account_activation_token
from django.contrib.auth import get_user_model

from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.shortcuts import render, redirect
from django.contrib import messages


import logging

logger = logging.getLogger("django_mcq")


User = get_user_model()


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False  # Deactivate account until confirmed
        user.save()

        current_site = get_current_site(self.request)
        subject = "Activate Your Account"
        message = render_to_string("registration/account_activation_email.html", {
            "user": user,
            "domain": current_site.domain,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": account_activation_token.make_token(user),
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

        return super().form_valid(form)


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect("login")  # or an "account activated" success page
    else:
        return render(request, "registration/account_activation_invalid.html")


class ResendActivationEmailView(FormView):
    template_name = 'registration/resend_activation.html'
    form_class = ResendActivationEmailForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                current_site = get_current_site(self.request)
                subject = 'Activate Your Account'
                message = render_to_string('registration/account_activation_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                messages.success(self.request, 'A new activation link has been sent to your email.')
            else:
                messages.info(self.request, 'This account is already active.')
        except User.DoesNotExist:
            messages.error(self.request, 'No account found with that email address.')

        return super().form_valid(form)
