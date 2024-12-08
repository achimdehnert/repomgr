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
    local_path = models.CharField(max_length=512, null=True, blank=True)
    _cached_active_session = None
    _cached_has_sessions = None

    class Meta:
        verbose_name_plural = "repositories"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['updated_at']),
            models.Index(fields=['organization']),
            models.Index(fields=['language']),
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.name  # Set full_name if not provided
        super().save(*args, **kwargs)

    @property
    def active_session(self):
        if self._cached_active_session is None:
            from django.db.models import Q
            from .models import WindsurfSession
            
            self._cached_active_session = self.sessions.filter(active=True).select_related('branch').first()
            print(f"Repository {self.name}: Active Session = {self._cached_active_session}")
            print(f"Total Sessions: {self.sessions.count()}")
        
        return self._cached_active_session

    @property
    def has_sessions(self):
        if self._cached_has_sessions is None:
            self._cached_has_sessions = self.sessions.exists()
            print(f"Repository {self.name}: Has Sessions = {self._cached_has_sessions}")
        
        return self._cached_has_sessions

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        self._cached_active_session = None
        self._cached_has_sessions = None

    @classmethod
    def search(cls, query=None, private=None, organization=None, language=None):
        """
        Advanced search for repositories with multiple filtering options
        
        Args:
            query (str, optional): Search term to match against name, description, or organization
            private (bool, optional): Filter by private status
            organization (str, optional): Filter by organization name
            language (str, optional): Filter by programming language
        
        Returns:
            QuerySet of matching repositories
        """
        # Start with a base queryset
        queryset = cls.objects.all()
        
        # Apply text-based search if query is provided
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(organization__icontains=query)
            )
        
        # Filter by private status if specified
        if private is not None:
            queryset = queryset.filter(private=private)
        
        # Filter by organization if specified
        if organization is not None:
            # Allow partial matching for organization
            queryset = queryset.filter(organization__icontains=organization)
        
        # Filter by language if specified
        if language is not None:
            queryset = queryset.filter(language__icontains=language)
        
        return queryset.distinct()

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

class WindsurfSession(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    last_file_accessed = models.CharField(max_length=500, blank=True, null=True)
    cursor_position = models.CharField(max_length=100, blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    environment_variables = models.JSONField(default=dict, blank=True)
    open_files = models.JSONField(default=list, blank=True)
    git_status = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        duration = ""
        if self.end_time:
            duration = f" (Duration: {self.end_time - self.start_time})"
        return f"Session for {self.repository.name} started at {self.start_time}{duration}"
    
    def save_current_state(self, files=None, cursor=None, env_vars=None):
        if files:
            self.open_files = files
        if cursor:
            self.cursor_position = cursor
        if env_vars:
            self.environment_variables = env_vars
        self.save()
    
    def end_session(self):
        self.end_time = timezone.now()
        self.active = False
        self.save()
