import click
from rich.console import Console
from rich.table import Table
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

class RepoManager:
    def __init__(self, github_token=None):
        """
        Initialize GitHub Repository Manager
        
        :param github_token: GitHub Personal Access Token
        """
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        
        if not self.github_token:
            console.print("[bold red]Error:[/] GitHub token not found. Set GITHUB_TOKEN environment variable.")
            raise ValueError("GitHub token is required")

    def list_repos(self, username=None):
        """
        List repositories for a given user
        
        :param username: GitHub username (defaults to token owner)
        """
        from github import Github
        
        try:
            g = Github(self.github_token)
            
            # Use token owner if no username provided
            if not username:
                username = g.get_user().login
            
            # Create a table for repository display
            table = Table(title=f"Repositories for {username}")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="magenta")
            table.add_column("Stars", style="green")
            table.add_column("Language", style="yellow")
            
            # Fetch and display repositories
            user = g.get_user(username)
            for repo in user.get_repos():
                table.add_row(
                    repo.name, 
                    repo.description or "No description", 
                    str(repo.stargazers_count),
                    repo.language or "Unknown"
                )
            
            console.print(table)
        
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")

    def create_repo(self, name, description=None, private=False):
        """
        Create a new repository
        
        :param name: Repository name
        :param description: Repository description
        :param private: Whether the repository is private
        """
        from github import Github
        
        try:
            g = Github(self.github_token)
            user = g.get_user()
            
            repo = user.create_repo(
                name, 
                description=description, 
                private=private
            )
            
            console.print(f"[bold green]Repository '{name}' created successfully![/]")
            console.print(f"URL: {repo.html_url}")
        
        except Exception as e:
            console.print(f"[bold red]Error creating repository:[/] {e}")

@click.group()
def cli():
    """GitHub Repository Management CLI"""
    pass

@cli.command()
@click.option('--username', help='GitHub username to list repositories for')
def list_repos(username):
    """List repositories for a user"""
    manager = RepoManager()
    manager.list_repos(username)

@cli.command()
@click.argument('name')
@click.option('--description', help='Repository description')
@click.option('--private/--public', default=False, help='Create a private or public repository')
def create_repo(name, description, private):
    """Create a new repository"""
    manager = RepoManager()
    manager.create_repo(name, description, private)

if __name__ == '__main__':
    cli()
