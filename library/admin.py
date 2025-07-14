from django.contrib import admin

from library.models import LibChat, LibMessage, LibDocuments, LibDocumentEmbeddings

admin.site.register(LibChat)
admin.site.register(LibMessage)
admin.site.register(LibDocuments)
admin.site.register(LibDocumentEmbeddings)
