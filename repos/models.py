from django.db import models
from django.utils import timezone

# Create your models here.

class Repository(models.Model):
    github_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, default='')  # Added default
    description = models.TextField(blank=True, null=True)
    url = models.URLField()
    private = models.BooleanField(default=False)
    fork = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    size = models.IntegerField(default=0)
    language = models.CharField(max_length=100, blank=True, null=True)
    default_branch = models.CharField(max_length=100, default='main')
    organization = models.CharField(max_length=255, null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "repositories"
        ordering = ['-updated_at']

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.name  # Set full_name if not provided
        super().save(*args, **kwargs)

    @classmethod
    def search(cls, query):
        """Search repositories by name, description, language, or organization"""
        return cls.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(language__icontains=query) |
            models.Q(organization__icontains=query)
        ).distinct()

class Branch(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)
    last_commit_sha = models.CharField(max_length=40)
    last_commit_message = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "branches"
        ordering = ['-updated_at']
        unique_together = ['repository', 'name']

    def __str__(self):
        return f"{self.repository.name}/{self.name}"
