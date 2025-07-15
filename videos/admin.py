from django.contrib import admin
from django.db.models import Count

from videos.models import Video

class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')
    list_filter = ('user',)
    search_fields = ('title', 'user__username')

    change_list_template = "admin/video_changelist.html"

    def changelist_view(self, request, extra_context=None):
        total_vids = Video.objects.count()
        videos_per_user = (
                Video.objects.values('user__username')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        extra_context = extra_context or {}
        extra_context['total_vids'] = total_vids
        extra_context['videos_per_user'] = videos_per_user

        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Video, VideoAdmin)

