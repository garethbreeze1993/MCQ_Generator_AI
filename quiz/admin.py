from django.contrib import admin
from django.db.models import Count
from quiz.models import Quiz, Question, Answer


class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    list_filter = ('user',)
    search_fields = ('title', 'user__username')

    change_list_template = "admin/quiz_changelist.html"

    def changelist_view(self, request, extra_context=None):
        total_quizzes = Quiz.objects.count()
        quizzes_per_user = (
            Quiz.objects.values('user__username')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        extra_context = extra_context or {}
        extra_context['total_quizzes'] = total_quizzes
        extra_context['quizzes_per_user'] = quizzes_per_user

        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question)
admin.site.register(Answer)
