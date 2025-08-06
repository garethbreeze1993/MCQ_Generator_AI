from django.views.generic.base import TemplateView
from .forms import ContactForm
from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings

class HomePageView(TemplateView):
    template_name = 'homepage.html'


def contact_view(request):
    success = False

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Extract form data
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Compose message
            full_message = f"From: {email}\n\n{message}\n\n"

            full_message += f"User is === {request.user}"

            # Send email
            send_mail(
                subject,
                full_message,
                settings.DEFAULT_FROM_EMAIL,  # From email
                [settings.CONTACT_FORM_RECIPIENT],  # To email
            )
            success = True
    else:
        form = ContactForm()

    return render(request, 'contact_form.html', {'form': form, 'success': success})
