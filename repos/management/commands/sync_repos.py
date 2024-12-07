from django.core.management.base import BaseCommand
from repos.services import GitHubService
from rich.console import Console
from rich.table import Table

class Command(BaseCommand):
    help = 'Synchronize GitHub repositories'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='GitHub username to sync repositories from')

    def handle(self, *args, **options):
        console = Console()
        
        with console.status("[bold green]Syncing repositories...") as status:
            service = GitHubService()
            try:
                repos = service.sync_repositories(username=options.get('username'))
                
                # Create table for output
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Repository")
                table.add_column("URL")
                table.add_column("Private")
                table.add_column("Branches")
                
                for repo in repos:
                    table.add_row(
                        repo.name,
                        repo.url,
                        "✓" if repo.private else "✗",
                        str(repo.branches.count())
                    )
                
                console.print("\n[bold green]Successfully synced repositories![/bold green]")
                console.print(table)
                
            except Exception as e:
                console.print(f"[bold red]Error syncing repositories: {str(e)}[/bold red]")
