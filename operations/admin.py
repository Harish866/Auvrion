
from django.contrib import admin
from .models import Agent, Task


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'agent',
        'priority',
        'status',
        'progress',
        'budget'
    )

    list_filter = ('status', 'priority', 'agent')
    search_fields = ('title',)
