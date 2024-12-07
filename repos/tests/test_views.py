from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from repos.models import Repository
from repos.forms import RepositoryImportForm

class TestViews(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create test repository
        self.repo = Repository.objects.create(
            github_id=1,
            name='test-repo',
            full_name='user/test-repo',
            url='https://github.com/user/test-repo',
            private=False,
            fork=False
        )

    def test_repository_list_view(self):
        # Test repository list view
        response = self.client.get(reverse('repos:repository_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'repos/repository_list.html')
        self.assertContains(response, 'test-repo')

    def test_repository_detail_view(self):
        # Test repository detail view
        response = self.client.get(
            reverse('repos:repository_detail', kwargs={'pk': self.repo.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'repos/repository_detail.html')
        self.assertContains(response, self.repo.name)

    @patch('repos.views.GitHubService')
    def test_repository_import_view_get(self, mock_github_service):
        # Test GET request to import view
        response = self.client.get(reverse('repos:repository_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'repos/repository_import.html')
        self.assertIsInstance(response.context['form'], RepositoryImportForm)

    @patch('repos.views.GitHubService')
    def test_repository_import_view_post_success(self, mock_github_service):
        # Mock successful repository import
        mock_instance = mock_github_service.return_value
        mock_instance.sync_repositories.return_value = [self.repo]
        
        response = self.client.post(reverse('repos:repository_import'), {
            'username': 'testuser',
            'include_private': True,
            'include_organization': True,
            'include_collaborations': True
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertRedirects(response, reverse('repos:repository_list'))
        mock_instance.sync_repositories.assert_called_once()

    @patch('repos.views.GitHubService')
    def test_repository_import_view_post_failure(self, mock_github_service):
        # Mock failed repository import
        mock_instance = mock_github_service.return_value
        mock_instance.sync_repositories.side_effect = Exception('Import failed')
        
        response = self.client.post(reverse('repos:repository_import'), {
            'username': 'testuser'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'repos/repository_import.html')
        self.assertContains(response, 'Error importing repositories')

    def test_repository_import_view_unauthenticated(self):
        # Test access without authentication
        self.client.logout()
        response = self.client.get(reverse('repos:repository_import'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_repository_filter(self):
        # Test repository filtering
        Repository.objects.create(
            github_id=2,
            name='private-repo',
            full_name='user/private-repo',
            url='https://github.com/user/private-repo',
            private=True
        )
        
        # Test filtering private repositories
        response = self.client.get(reverse('repos:repository_list') + '?show_private=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'private-repo')
        
        # Test filtering public repositories
        response = self.client.get(reverse('repos:repository_list') + '?show_private=false')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-repo')
        self.assertNotContains(response, 'private-repo')
