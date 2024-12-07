from github import Github
from django.conf import settings
from django.utils import timezone
from .models import Repository, Branch
import logging
import os

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        token = os.environ.get('GITHUB_ACCESS_TOKEN')
        if not token:
            raise ValueError("GitHub access token is not set in environment")
        
        try:
            # Initialize with higher per_page setting and retry settings
            self.client = Github(
                token,
                per_page=100,  # Maximum items per page
                retry=3,       # Number of retries for failed requests
                timeout=15,    # Timeout in seconds
            )
            # Test the connection and log user info
            self.user = self.client.get_user()
            logger.info(f"Connected to GitHub as user: {self.user.login}")
            logger.info(f"Rate limit: {self.client.get_rate_limit().core.remaining}/{self.client.get_rate_limit().core.limit}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            raise ValueError(f"Failed to connect to GitHub: {str(e)}")

    def sync_repositories(self, username=None, affiliation='owner,organization_member,collaborator'):
        """Sync repositories for a specific user or all accessible repositories"""
        try:
            all_repos = set()  # Use a set to avoid duplicates

            # 1. Get user's own repositories
            logger.info("Fetching owned repositories...")
            owned_repos = self.user.get_repos(type='owner')
            for repo in owned_repos:
                all_repos.add(repo)
                logger.debug(f"Found owned repository: {repo.full_name}")

            # 2. Get repositories from organizations
            logger.info("Fetching organization repositories...")
            for org in self.user.get_orgs():
                logger.info(f"Checking organization: {org.login}")
                try:
                    org_repos = org.get_repos()
                    for repo in org_repos:
                        all_repos.add(repo)
                        logger.debug(f"Found org repository: {repo.full_name}")
                except Exception as e:
                    logger.error(f"Error fetching repos for org {org.login}: {str(e)}")

            # 3. Get repositories where user is a collaborator
            logger.info("Fetching collaborative repositories...")
            collab_repos = self.user.get_repos(type='collaborator')
            for repo in collab_repos:
                all_repos.add(repo)
                logger.debug(f"Found collaborative repository: {repo.full_name}")

            # 4. Get public repositories if a specific username is provided
            if username and username != self.user.login:
                logger.info(f"Fetching repositories for user {username}...")
                target_user = self.client.get_user(username)
                user_repos = target_user.get_repos()
                for repo in user_repos:
                    all_repos.add(repo)
                    logger.debug(f"Found user repository: {repo.full_name}")

            logger.info(f"Total unique repositories found: {len(all_repos)}")
            
            # Convert set to list for further processing
            all_repos = list(all_repos)
            
            synced_repos = []
            for repo in all_repos:
                try:
                    logger.info(f"Processing repository: {repo.full_name}")
                    # Create or update repository
                    repo_obj, created = Repository.objects.update_or_create(
                        github_id=repo.id,
                        defaults={
                            'name': repo.name,
                            'full_name': repo.full_name,
                            'description': repo.description or '',
                            'url': repo.html_url,
                            'private': repo.private,
                            'fork': repo.fork,
                            'created_at': repo.created_at,
                            'updated_at': repo.updated_at,
                            'pushed_at': repo.pushed_at,
                            'size': repo.size,
                            'language': repo.language or '',
                            'default_branch': repo.default_branch,
                            'organization': repo.organization.login if repo.organization else None,
                            'last_synced': timezone.now(),
                        }
                    )

                    # Update branches
                    self._sync_branches(repo_obj, repo)
                    synced_repos.append(repo_obj)
                    logger.info(f"Successfully synced repository: {repo.full_name}")
                except Exception as e:
                    logger.error(f"Error syncing repository {repo.full_name}: {str(e)}")
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
        repo_obj, _ = Repository.objects.update_or_create(
            github_id=github_repo.id,
            defaults={
                'name': github_repo.name,
                'description': github_repo.description,
                'url': github_repo.html_url,
                'private': github_repo.private,
                'last_synced': timezone.now(),
            }
        )
        self._sync_branches(repo_obj, github_repo)
        return repo_obj

    def delete_repository(self, repository):
        """Delete a repository from GitHub"""
        github_repo = self.client.get_repo(f"{self.client.get_user().login}/{repository.name}")
        github_repo.delete()
        repository.delete()

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
