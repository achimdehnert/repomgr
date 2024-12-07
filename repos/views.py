from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Repository, Branch
from .forms import (
    RepositoryForm,
    RepositoryImportForm,
    RepositoryCreateForm,
    RepositorySearchForm
)
from .services import GitHubService
from github import GithubException
import logging

logger = logging.getLogger(__name__)

@login_required
def repository_list(request):
    form = RepositorySearchForm(request.GET)
    repositories = Repository.objects.all()

    if form.is_valid() and form.cleaned_data['query']:
        query = form.cleaned_data['query']
        repositories = Repository.search(query)

    # Apply sorting
    sort = request.GET.get('sort', '-updated_at')
    if sort in ['name', '-name', 'updated_at', '-updated_at', 'language', '-language']:
        repositories = repositories.order_by(sort)

    return render(request, 'repos/repository_list.html', {
        'repositories': repositories,
        'search_form': form,
        'current_sort': sort
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
                
                # Always include all types of repositories
                affiliation = 'owner,organization_member,collaborator'
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
                    f'Successfully imported {len(repos)} repositories ' +
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
