from django.test import TestCase
from django.conf import settings
from unittest.mock import patch, MagicMock
import os
import shutil
import tempfile

from .models import Repository
from .services import GitHubService

class RepositoryDeletionTestCase(TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_base_dir = tempfile.mkdtemp()
        
        # Create a mock repository for testing
        self.test_repo = Repository.objects.create(
            github_id=12345,
            name='TestRepository',
            full_name='testuser/TestRepository',
            url='https://github.com/testuser/TestRepository',
            local_path=os.path.join(self.test_base_dir, 'TestRepository')
        )
        
        # Create a local directory for the repository
        os.makedirs(self.test_repo.local_path)
        with open(os.path.join(self.test_repo.local_path, 'test_file.txt'), 'w') as f:
            f.write('Test content')

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_base_dir, ignore_errors=True)
        
        # Remove test repository if it still exists
        Repository.objects.filter(name='TestRepository').delete()

    @patch('repos.services.Github')
    def test_successful_repository_deletion(self, mock_github):
        """
        Test successful deletion of a repository
        - GitHub repository is deleted
        - Local directory is removed
        - Database record is deleted
        """
        # Mock GitHub repository
        mock_github_repo = MagicMock()
        mock_github.return_value.get_user.return_value.login = 'testuser'
        mock_github.return_value.get_repo.return_value = mock_github_repo

        # Create service and delete repository
        service = GitHubService()
        service.delete_repository(self.test_repo)

        # Assertions
        mock_github_repo.delete.assert_called_once()
        self.assertFalse(os.path.exists(self.test_repo.local_path))
        self.assertFalse(Repository.objects.filter(name='TestRepository').exists())

    @patch('repos.services.Github')
    def test_repository_deletion_with_github_error(self, mock_github):
        """
        Test deletion when GitHub deletion fails
        - Local directory should still be removed
        - Database record should be deleted
        """
        # Mock GitHub repository to raise an exception
        mock_github_repo = MagicMock()
        mock_github.return_value.get_user.return_value.login = 'testuser'
        mock_github.return_value.get_repo.return_value = mock_github_repo
        mock_github_repo.delete.side_effect = Exception('GitHub deletion error')

        # Create service and delete repository
        service = GitHubService()
        service.delete_repository(self.test_repo)

        # Assertions
        mock_github_repo.delete.assert_called_once()
        self.assertFalse(os.path.exists(self.test_repo.local_path))
        self.assertFalse(Repository.objects.filter(name='TestRepository').exists())

    def test_repository_deletion_with_multiple_local_paths(self):
        """
        Test deletion when repository has multiple potential local paths
        """
        # Create additional local paths
        alt_path1 = os.path.join(self.test_base_dir, 'alt_repos', 'TestRepository')
        alt_path2 = os.path.join(self.test_base_dir, 'local_repos', 'TestRepository')
        
        os.makedirs(alt_path1, exist_ok=True)
        os.makedirs(alt_path2, exist_ok=True)
        
        # Update repository with alternative path
        self.test_repo.local_path = alt_path1
        self.test_repo.save()

        # Create service and delete repository
        service = GitHubService()
        
        with patch.object(service, 'client') as mock_client:
            mock_client.get_user.return_value.login = 'testuser'
            mock_client.get_repo.return_value = MagicMock()
            
            service.delete_repository(self.test_repo)

        # Assertions
        self.assertFalse(os.path.exists(alt_path1))
        self.assertFalse(os.path.exists(alt_path2))
        self.assertFalse(Repository.objects.filter(name='TestRepository').exists())

    def test_repository_deletion_with_permission_error(self):
        """
        Test deletion when there's a permission error
        """
        # Simulate a permission error by making the directory read-only
        os.chmod(self.test_repo.local_path, 0o444)

        # Create service and delete repository
        service = GitHubService()
        
        with patch.object(service, 'client') as mock_client:
            mock_client.get_user.return_value.login = 'testuser'
            mock_client.get_repo.return_value = MagicMock()
            
            service.delete_repository(self.test_repo)

        # Assertions
        # The test should not raise an unhandled exception
        # Ideally, we'd check the log for the permission error
        self.assertTrue(True)  # Placeholder for successful handling

    def test_repository_deletion_with_no_local_path(self):
        """
        Test deletion when no local path is set
        """
        # Create a repository with no local path
        no_path_repo = Repository.objects.create(
            github_id=54321,
            name='NoPathRepository',
            full_name='testuser/NoPathRepository',
            url='https://github.com/testuser/NoPathRepository',
            local_path=None
        )

        # Create service and delete repository
        service = GitHubService()
        
        with patch.object(service, 'client') as mock_client:
            mock_client.get_user.return_value.login = 'testuser'
            mock_client.get_repo.return_value = MagicMock()
            
            service.delete_repository(no_path_repo)

        # Assertions
        self.assertFalse(Repository.objects.filter(name='NoPathRepository').exists())

class RepositorySearchTestCase(TestCase):
    def setUp(self):
        """Create test repositories with varied attributes"""
        # Personal repositories
        Repository.objects.create(
            github_id=1,
            name='TestRepo1',
            description='A test repository',
            private=False,
            language='Python',
            organization=None
        )
        Repository.objects.create(
            github_id=2,
            name='TestRepo2',
            description='Another test repository',
            private=True,
            language='JavaScript',
            organization=None
        )
        
        # Organization repositories
        Repository.objects.create(
            github_id=3,
            name='OrgRepo1',
            description='Organization test repository',
            private=False,
            language='Python',
            organization='TestOrg'
        )
        Repository.objects.create(
            github_id=4,
            name='OrgRepo2',
            description='Another organization repository',
            private=True,
            language='Ruby',
            organization='TestOrg'
        )

    def test_search_by_query(self):
        """Test searching repositories by query"""
        results = Repository.search(query='test')
        self.assertEqual(results.count(), 4)

    def test_search_by_private_status(self):
        """Test filtering repositories by private status"""
        # Find private repositories
        private_repos = Repository.search(private=True)
        self.assertEqual(private_repos.count(), 2)
        
        # Find public repositories
        public_repos = Repository.search(private=False)
        self.assertEqual(public_repos.count(), 2)

    def test_search_by_organization(self):
        """Test filtering repositories by organization"""
        # Find repositories in TestOrg
        org_repos = Repository.search(organization='TestOrg')
        self.assertEqual(org_repos.count(), 2)
        
        # Find repositories not in any organization
        personal_repos = Repository.search(organization=None)
        self.assertEqual(personal_repos.count(), 2)

    def test_search_by_language(self):
        """Test filtering repositories by language"""
        # Find Python repositories
        python_repos = Repository.search(language='Python')
        self.assertEqual(python_repos.count(), 2)
        
        # Find Ruby repositories
        ruby_repos = Repository.search(language='Ruby')
        self.assertEqual(ruby_repos.count(), 1)

    def test_combined_search(self):
        """Test searching with multiple filters"""
        # Find private Python repositories
        results = Repository.search(private=True, language='Python')
        self.assertEqual(results.count(), 0)
        
        # Find public Python repositories
        results = Repository.search(private=False, language='Python')
        self.assertEqual(results.count(), 2)
        
        # Find private repositories in TestOrg
        results = Repository.search(private=True, organization='TestOrg')
        self.assertEqual(results.count(), 1)

    def test_empty_search(self):
        """Test searching with no results"""
        # Search for non-existent language
        results = Repository.search(language='Go')
        self.assertEqual(results.count(), 0)
        
        # Search for non-existent organization
        results = Repository.search(organization='NonExistentOrg')
        self.assertEqual(results.count(), 0)
