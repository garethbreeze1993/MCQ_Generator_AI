from django.contrib import admin

from chatbot.models import Chat, Message

from django.db.models import Count

class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    list_filter = ('user',)
    search_fields = ('title', 'user__username')

    change_list_template = "admin/chat_changelist.html"

    def changelist_view(self, request, extra_context=None):
        total_chats = Chat.objects.count()
        chats_per_user = (
                Chat.objects.values('user__username')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        extra_context = extra_context or {}
        extra_context['total_chats'] = total_chats
        extra_context['chats_per_user'] = chats_per_user

        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Chat, ChatAdmin)
admin.site.register(Message)

