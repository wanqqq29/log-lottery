from django.contrib import admin

from .models import (
    Customer,
    DrawBatch,
    DrawWinner,
    ExclusionRule,
    ExportJob,
    Prize,
    Project,
    ProjectMember,
)

admin.site.register(Customer)
admin.site.register(Project)
admin.site.register(ProjectMember)
admin.site.register(Prize)
admin.site.register(DrawBatch)
admin.site.register(DrawWinner)
admin.site.register(ExclusionRule)
admin.site.register(ExportJob)
