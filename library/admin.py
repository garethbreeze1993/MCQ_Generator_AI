from django.contrib import admin

from library.models import LibChat, LibMessage, LibDocuments, LibDocumentEmbeddings

from django.db.models import Count


class LibChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    list_filter = ('user',)
    search_fields = ('title', 'user__username')

    change_list_template = "admin/libchat_changelist.html"

    def changelist_view(self, request, extra_context=None):
        total_libchats = LibChat.objects.count()
        libchats_per_user = (
                LibChat.objects.values('user__username')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        extra_context = extra_context or {}
        extra_context['total_libchats'] = total_libchats
        extra_context['libchats_per_user'] = libchats_per_user

        return super().changelist_view(request, extra_context=extra_context)



class LibDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    list_filter = ('user',)
    search_fields = ('name', 'user__username')

    change_list_template = "admin/libdoc_changelist.html"

    def changelist_view(self, request, extra_context=None):
        total_docs = LibDocuments.objects.count()
        docs_per_user = (
                LibDocuments.objects.values('user__username')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        extra_context = extra_context or {}
        extra_context['total_docs'] = total_docs
        extra_context['docs_per_user'] = docs_per_user

        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(LibChat, LibChatAdmin)
admin.site.register(LibMessage)
admin.site.register(LibDocuments, LibDocumentAdmin)
admin.site.register(LibDocumentEmbeddings)
