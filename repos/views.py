from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Repository, Branch, WindsurfSession
from .forms import (
    RepositoryForm,
    RepositoryImportForm,
    RepositoryCreateForm,
    RepositorySearchForm,
    WindsurfSessionForm
)
from .services import GitHubService
from github import GithubException
import logging
from django.utils import timezone
import git
from django.db.models import Q, Prefetch

logger = logging.getLogger(__name__)

@login_required
def repository_list(request):
    # Initialize session search status if not exists
    if 'search_status' not in request.session:
        request.session['search_status'] = {
            'query': '',
            'private': '',
            'organization': '',
            'total_repositories': 0,
            'filtered_repositories': 0,
            'last_search_time': None
        }

    form = RepositorySearchForm(request.GET)
    
    # Start with an optimized queryset
    repositories = Repository.objects.prefetch_related(
        Prefetch(
            'sessions',
            queryset=WindsurfSession.objects.filter(active=True).select_related('branch'),
            to_attr='_prefetched_active_sessions'
        )
    ).all()

    # Update search status
    search_status = request.session['search_status']
    search_status['last_search_time'] = timezone.now().isoformat()
    search_status['total_repositories'] = repositories.count()

    if form.is_valid():
        # Text-based search
        query = form.cleaned_data.get('query', '')
        search_status['query'] = query
        if query:
            repositories = repositories.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(organization__icontains=query)
            )

        # Private status filter
        private_filter = form.cleaned_data.get('private', '')
        search_status['private'] = private_filter
        if private_filter == 'true':
            repositories = repositories.filter(private=True)
        elif private_filter == 'false':
            repositories = repositories.filter(private=False)

        # Organization filter
        organization = form.cleaned_data.get('organization', '')
        search_status['organization'] = organization
        if organization:
            repositories = repositories.filter(organization__icontains=organization)

    # Update filtered repositories count
    search_status['filtered_repositories'] = repositories.count()
    request.session.modified = True

    # Apply sorting
    sort = request.GET.get('sort', '-updated_at')
    if sort in ['name', '-name', 'updated_at', '-updated_at', 'language', '-language']:
        repositories = repositories.order_by(sort)

    return render(request, 'repos/repository_list.html', {
        'repositories': repositories,
        'search_form': form,
        'current_sort': sort,
        'search_status': search_status
    })

@login_required
def repository_detail(request, pk):
    repository = get_object_or_404(Repository, pk=pk)
    branches = repository.branches.all().order_by('-is_default', 'name')
    return render(request, 'repos/repository_detail.html', {
        'repository': repository,
        'branches': branches
    })

@login_required
def repository_import(request):
    logger.info(f"Import request method: {request.method}")
    if request.method == 'POST':
        form = RepositoryImportForm(request.POST)
        logger.info(f"Form data: {request.POST}")
        if form.is_valid():
            logger.info("Form is valid")
            try:
                service = GitHubService()
                logger.info("GitHubService initialized")
                
                # Set affiliation to 'owner' only
                affiliation = 'owner'
                logger.info(f"Using affiliation: {affiliation}")
                
                # Get repositories based on form data
                username = form.cleaned_data.get('username')
                logger.info(f"Importing for username: {username if username else 'current user'}")
                
                repos = service.sync_repositories(
                    username=username,
                    affiliation=affiliation
                )
                logger.info(f"Initial repos fetched: {len(repos)}")
                
                # Filter repositories based on form options
                if not form.cleaned_data['include_private']:
                    repos = [r for r in repos if not r.private]
                if not form.cleaned_data['include_organization']:
                    repos = [r for r in repos if not r.organization]
                if not form.cleaned_data['include_collaborations']:
                    user = service.client.get_user().login
                    repos = [r for r in repos if user in r.full_name or (r.organization and form.cleaned_data['include_organization'])]
                
                logger.info(f"After filtering: {len(repos)} repos")
                
                messages.success(
                    request,
                    f'Import of {len(repos)} repositories completed successfully! ' +
                    f'({sum(1 for r in repos if r.private)} private, ' +
                    f'{sum(1 for r in repos if r.organization)} from organizations)'
                )
                return redirect('repos:repository_list')
            except Exception as e:
                logger.error(f"Error during import: {str(e)}", exc_info=True)
                messages.error(request, f'Error importing repositories: {str(e)}')
        else:
            logger.error(f"Form validation errors: {form.errors}")
    else:
        form = RepositoryImportForm()
        logger.info("Displaying empty import form")
    
    return render(request, 'repos/repository_import.html', {'form': form})

@login_required
def repository_create(request):
    if request.method == 'POST':
        form = RepositoryCreateForm(request.POST)
        if form.is_valid():
            try:
                service = GitHubService()
                repo = service.create_repository(
                    name=form.cleaned_data['name'],
                    description=form.cleaned_data['description'],
                    private=form.cleaned_data['private'],
                    auto_init=form.cleaned_data['auto_init']
                )
                messages.success(request, f'Successfully created repository {repo.name}')
                return redirect('repos:repository_detail', pk=repo.pk)
            except GithubException as e:
                messages.error(request, f'Error creating repository: {str(e)}')
    else:
        form = RepositoryCreateForm()
    
    return render(request, 'repos/repository_create.html', {'form': form})

@login_required
def repository_delete(request, pk):
    repository = get_object_or_404(Repository, pk=pk)
    if request.method == 'POST':
        try:
            service = GitHubService()
            service.delete_repository(repository)
            messages.success(request, f'Successfully deleted repository {repository.name}')
            return redirect('repos:repository_list')
        except GithubException as e:
            messages.error(request, f'Error deleting repository: {str(e)}')
    
    return render(request, 'repos/repository_delete.html', {'repository': repository})

@login_required
def start_session(request, pk):
    repository = get_object_or_404(Repository, pk=pk)
    
    # End any active sessions for this repository
    WindsurfSession.objects.filter(repository=repository, active=True).update(
        active=False,
        end_time=timezone.now()
    )
    
    # Create new session
    session = WindsurfSession.objects.create(
        repository=repository,
        branch=repository.branches.filter(is_default=True).first()
    )
    
    # Get git status
    try:
        repo = git.Repo(repository.local_path)
        session.git_status = {
            'branch': repo.active_branch.name,
            'modified': [item.a_path for item in repo.index.diff(None)],
            'untracked': repo.untracked_files
        }
        session.save()
    except Exception as e:
        logger.error(f"Error getting git status: {str(e)}")
    
    messages.success(request, f'Started new Windsurf session for {repository.name}')
    return redirect('repos:repository_detail', pk=pk)

@login_required
def end_session(request, pk, session_id):
    repository = get_object_or_404(Repository, pk=pk)
    session = get_object_or_404(WindsurfSession, pk=session_id, repository=repository)
    
    if request.method == 'POST':
        form = WindsurfSessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save(commit=False)
            session.end_session()
            messages.success(request, f'Ended Windsurf session for {repository.name}')
            return redirect('repos:repository_detail', pk=pk)
    else:
        form = WindsurfSessionForm(instance=session)
    
    return render(request, 'repos/session_end.html', {
        'form': form,
        'repository': repository,
        'session': session
    })

@login_required
def session_list(request, pk):
    repository = get_object_or_404(Repository, pk=pk)
    sessions = repository.sessions.all()
    return render(request, 'repos/session_list.html', {
        'repository': repository,
        'sessions': sessions
    })
