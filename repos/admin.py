from django.contrib import admin
from .models import Repository, Branch

# Register your models here.

@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'private', 'created_at', 'last_synced')
    list_filter = ('private', 'created_at', 'last_synced')
    search_fields = ('name', 'description')
    readonly_fields = ('github_id', 'created_at', 'updated_at', 'last_synced')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'repository', 'is_default', 'last_commit_sha', 'updated_at')
    list_filter = ('is_default', 'repository', 'updated_at')
    search_fields = ('name', 'repository__name', 'last_commit_message')
    readonly_fields = ('last_commit_sha', 'updated_at')
