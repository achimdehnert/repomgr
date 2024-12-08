from github import Github
from django.conf import settings
from django.utils import timezone
from .models import Repository, Branch
import logging
import os
import shutil
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.token = os.environ.get('GITHUB_ACCESS_TOKEN')
        if not self.token:
            raise ValueError("GitHub access token is not set in environment")
        
        try:
            # Initialize PyGithub client for some operations
            self.client = Github(self.token)
            self.user = self.client.get_user()
            logger.info(f"Connected to GitHub as user: {self.user.login}")
            
            # Create local repos directory if it doesn't exist
            os.makedirs(settings.LOCAL_REPOS_DIR, exist_ok=True)
            logger.info(f"Local repositories directory: {settings.LOCAL_REPOS_DIR}")
            
            # Set up session for direct API calls
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Python'
            })
            
            # Test API access
            response = self.session.get('https://api.github.com/user')
            response.raise_for_status()
            logger.info(f"API connection successful. Rate limit: {self.client.get_rate_limit().core.remaining}/{self.client.get_rate_limit().core.limit}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            raise ValueError(f"Failed to connect to GitHub: {str(e)}")

    def _get_all_pages(self, url, params=None):
        """Helper method to handle GitHub API pagination using Link headers"""
        if params is None:
            params = {}
        params['per_page'] = 100  # Set this once at the start
        
        all_items = []
        current_url = url
        
        while current_url:
            # For the first request, use the original URL with params
            # For subsequent requests, use the full next_url from Link header (which already includes params)
            if current_url == url:
                response = self.session.get(current_url, params=params)
            else:
                response = self.session.get(current_url)
            
            # Check rate limit before parsing response
            rate_limit = response.headers.get('X-RateLimit-Remaining')
            if rate_limit and int(rate_limit) == 0:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                current_time = int(timezone.now().timestamp())
                wait_time = reset_time - current_time
                raise Exception(f"GitHub API rate limit exceeded. Reset in {wait_time} seconds")
            
            response.raise_for_status()
            logger.info(f"Rate limit remaining: {rate_limit}")
            
            # Get items from current page
            items = response.json()
            if not isinstance(items, list):
                break
                
            if not items:  # No items in response
                break
                
            all_items.extend(items)
            logger.debug(f"Fetched {len(items)} items")
            
            # Check for next page in Link header
            current_url = None
            if 'Link' in response.headers:
                links = response.headers['Link'].split(', ')
                for link in links:
                    if 'rel="next"' in link:
                        current_url = link[link.index('<') + 1:link.index('>')]
                        logger.debug(f"Found next page: {current_url}")
                        break
            
            if not current_url:
                logger.debug("No more pages to fetch")
                break
        
        return all_items

    def sync_repositories(self, username=None, affiliation='owner'):
        """Sync repositories for a specific user or all accessible repositories"""
        try:
            # Get all repositories using direct API call with proper pagination
            logger.info("Fetching all accessible repositories...")
            repos_data = self._get_all_pages(
                'https://api.github.com/user/repos',
                params={'affiliation': affiliation, 'sort': 'full_name'}
            )
            
            # Also get starred repositories
            logger.info("Fetching starred repositories...")
            starred_repos = self._get_all_pages('https://api.github.com/user/starred')
            
            # Combine and deduplicate repositories
            all_repos = repos_data + starred_repos
            seen_ids = set()
            unique_repos = []
            for repo in all_repos:
                if repo['id'] not in seen_ids:
                    seen_ids.add(repo['id'])
                    unique_repos.append(repo)
            
            logger.info(f"Total unique repositories found: {len(unique_repos)}")
            logger.info("Repository IDs found:")
            for repo in unique_repos:
                logger.info(f"ID: {repo['id']} - {repo['full_name']}")
            
            synced_repos = []
            for repo_data in unique_repos:
                try:
                    logger.info(f"Processing repository: {repo_data['full_name']}")
                    
                    # Parse dates
                    created_at = datetime.strptime(repo_data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    updated_at = datetime.strptime(repo_data['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
                    pushed_at = datetime.strptime(repo_data['pushed_at'], '%Y-%m-%dT%H:%M:%SZ') if repo_data['pushed_at'] else None
                    
                    # Determine the actual local path
                    local_path = os.path.join(os.path.dirname(settings.BASE_DIR), repo_data['name'])
                    logger.info(f"Actual local path for {repo_data['name']}: {local_path}")
                    
                    # Create or update repository
                    repo_obj, created = Repository.objects.update_or_create(
                        github_id=repo_data['id'],
                        defaults={
                            'name': repo_data['name'],
                            'full_name': repo_data['full_name'],
                            'description': repo_data['description'] or '',
                            'url': repo_data['html_url'],
                            'private': repo_data['private'],
                            'fork': repo_data['fork'],
                            'created_at': created_at,
                            'updated_at': updated_at,
                            'pushed_at': pushed_at,
                            'size': repo_data['size'],
                            'language': repo_data['language'] or '',
                            'default_branch': repo_data['default_branch'],
                            'organization': repo_data['owner']['login'] if repo_data['owner']['type'] == 'Organization' else None,
                            'last_synced': timezone.now(),
                            'local_path': local_path
                        }
                    )
                    
                    # Verify local directory exists
                    if os.path.exists(local_path):
                        logger.info(f"Local directory exists: {local_path}")
                    else:
                        logger.warning(f"Local directory does not exist: {local_path}")

                    # Get repository object for branch syncing
                    github_repo = self.client.get_repo(repo_data['full_name'])
                    self._sync_branches(repo_obj, github_repo)
                    
                    synced_repos.append(repo_obj)
                    logger.info(f"Successfully synced repository: {repo_data['full_name']}")
                except Exception as e:
                    logger.error(f"Error syncing repository {repo_data['full_name']}: {str(e)}")
                    continue

            # Log summary
            logger.info(f"Sync complete. Total repositories synced: {len(synced_repos)}")
            logger.info(f"Private repos: {sum(1 for r in synced_repos if r.private)}")
            logger.info(f"Organization repos: {sum(1 for r in synced_repos if r.organization)}")
            
            return synced_repos
        except Exception as e:
            logger.error(f"Error in sync_repositories: {str(e)}")
            raise

    def _sync_branches(self, repo_obj, github_repo):
        """Sync branches for a specific repository"""
        try:
            # Get all branches for the repository
            branches = list(github_repo.get_branches())
            
            # Keep track of existing branches
            existing_branches = set()
            
            for branch in branches:
                try:
                    branch_obj, _ = Branch.objects.update_or_create(
                        repository=repo_obj,
                        name=branch.name,
                        defaults={
                            'is_default': branch.name == github_repo.default_branch,
                            'last_commit_sha': branch.commit.sha,
                            'last_commit_message': branch.commit.commit.message if branch.commit.commit else '',
                        }
                    )
                    existing_branches.add(branch.name)
                except Exception as e:
                    logger.error(f"Error syncing branch {branch.name} for repo {repo_obj.full_name}: {str(e)}")
                    continue

            # Remove branches that no longer exist
            repo_obj.branches.exclude(name__in=existing_branches).delete()
            
            logger.info(f"Synced {len(existing_branches)} branches for {repo_obj.full_name}")
        except Exception as e:
            logger.error(f"Error in _sync_branches for {repo_obj.full_name}: {str(e)}")
            raise

    def create_repository(self, name, description=None, private=False, auto_init=True):
        """Create a new repository on GitHub"""
        github_repo = self.client.get_user().create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=auto_init
        )
        
        # Sync the newly created repository
        local_path = os.path.join(os.path.dirname(settings.BASE_DIR), github_repo.name)
        logger.info(f"Setting local path for new repository: {local_path}")
        
        repo_obj, _ = Repository.objects.update_or_create(
            github_id=github_repo.id,
            defaults={
                'name': github_repo.name,
                'description': github_repo.description,
                'url': github_repo.html_url,
                'private': github_repo.private,
                'last_synced': timezone.now(),
                'local_path': local_path
            }
        )
        
        # Ensure local directory exists
        if os.path.exists(local_path):
            logger.info(f"Local directory exists: {local_path}")
        else:
            logger.warning(f"Local directory does not exist: {local_path}")

        self._sync_branches(repo_obj, github_repo)
        return repo_obj

    def delete_repository(self, repository):
        """Delete a repository from GitHub and remove its local folder if it exists"""
        try:
            # First, delete from GitHub
            github_repo = self.client.get_repo(f"{self.client.get_user().login}/{repository.name}")
            github_repo.delete()
            logger.info(f"Successfully deleted GitHub repository: {repository.name}")
        except Exception as github_delete_error:
            logger.error(f"Error deleting GitHub repository {repository.name}: {str(github_delete_error)}")
        
        # Delete local folder if it exists
        local_paths_to_check = [
            repository.local_path,  # Path from database
            os.path.join(settings.LOCAL_REPOS_DIR, repository.name),  # Default local repos directory
            os.path.join(settings.BASE_DIR, 'local_repos', repository.name)  # Alternative local repos path
        ]
        
        for local_path in local_paths_to_check:
            if not local_path:
                continue
            
            logger.info(f"Checking local path for deletion: {local_path}")
            
            try:
                # Ensure we're not trying to delete something outside the intended directory
                base_github_dir = os.path.dirname(settings.BASE_DIR)
                if not local_path.startswith(base_github_dir):
                    logger.warning(f"Local path {local_path} is not within {base_github_dir}. Skipping deletion.")
                    continue
                
                if not os.path.exists(local_path):
                    logger.warning(f"Local folder does not exist: {local_path}")
                    continue
                
                # Check if it's a directory
                if not os.path.isdir(local_path):
                    logger.warning(f"Local path is not a directory: {local_path}")
                    continue
                
                # Detailed directory contents logging
                logger.info(f"Directory contents of {local_path}:")
                for item in os.listdir(local_path):
                    logger.info(f"  - {item}")
                
                # Use shutil to remove the entire directory
                import shutil
                shutil.rmtree(local_path)
                logger.info(f"Successfully deleted local folder: {local_path}")
                break  # Stop after successfully deleting one path
            except PermissionError:
                logger.error(f"Permission denied when trying to delete {local_path}")
            except Exception as delete_error:
                logger.error(f"Error deleting local folder {local_path}: {str(delete_error)}")
        
        # Finally, remove from database
        try:
            repository.delete()
            logger.info(f"Successfully removed repository {repository.name} from database")
        except Exception as db_delete_error:
            logger.error(f"Error removing repository from database: {str(db_delete_error)}")

    def get_repository_details(self, repository):
        """Get detailed information about a repository"""
        github_repo = self.client.get_repo(f"{self.client.get_user().login}/{repository.name}")
        return {
            'stars': github_repo.stargazers_count,
            'forks': github_repo.forks_count,
            'open_issues': github_repo.open_issues_count,
            'watchers': github_repo.watchers_count,
            'default_branch': github_repo.default_branch,
            'language': github_repo.language,
            'created_at': github_repo.created_at,
            'updated_at': github_repo.updated_at,
            'pushed_at': github_repo.pushed_at,
        }
