from django.contrib import admin

from quiz.models import Quiz, Question, Answer

admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
