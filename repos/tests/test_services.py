import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from repos.services import GitHubService
from repos.models import Repository, Branch

class TestGitHubService(TestCase):
    def setUp(self):
        # Mock environment variable
        self.env_patcher = patch.dict('os.environ', {'GITHUB_ACCESS_TOKEN': 'fake-token'})
        self.env_patcher.start()
        
        # Create test repositories
        self.repo1 = Repository.objects.create(
            github_id=1,
            name='test-repo-1',
            full_name='user/test-repo-1',
            url='https://github.com/user/test-repo-1',
            private=False,
            fork=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            pushed_at=timezone.now(),
            size=1000,
            language='Python',
            default_branch='main'
        )
        
        self.repo2 = Repository.objects.create(
            github_id=2,
            name='test-repo-2',
            full_name='org/test-repo-2',
            url='https://github.com/org/test-repo-2',
            private=True,
            fork=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            pushed_at=timezone.now(),
            size=2000,
            language='JavaScript',
            default_branch='main',
            organization='test-org'
        )

    def tearDown(self):
        self.env_patcher.stop()
        Repository.objects.all().delete()
        Branch.objects.all().delete()

    @patch('repos.services.Github')
    @patch('repos.services.requests.Session')
    def test_init_success(self, mock_session, mock_github):
        # Test successful initialization
        mock_user = MagicMock()
        mock_user.login = 'test-user'
        mock_github.return_value.get_user.return_value = mock_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        
        service = GitHubService()
        self.assertIsNotNone(service.client)
        self.assertEqual(service.user.login, 'test-user')

    @patch('repos.services.Github')
    def test_init_failure(self, mock_github):
        # Test initialization failure
        mock_github.return_value.get_user.side_effect = Exception('API Error')
        
        with self.assertRaises(ValueError):
            GitHubService()

    @patch('repos.services.Github')
    @patch('repos.services.requests.Session')
    def test_get_all_pages(self, mock_session, mock_github):
        # Test pagination handling
        mock_response1 = MagicMock()
        mock_response1.json.return_value = [{'id': 1, 'name': 'repo1'}]
        mock_response1.headers = {
            'Link': '<https://api.github.com/user/repos?page=2>; rel="next"',
            'X-RateLimit-Remaining': '4999'
        }
        mock_response1.status_code = 200
        
        mock_response2 = MagicMock()
        mock_response2.json.return_value = [{'id': 2, 'name': 'repo2'}]
        mock_response2.headers = {
            'X-RateLimit-Remaining': '4998'
        }
        mock_response2.status_code = 200
        
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.headers = {'X-RateLimit-Remaining': '5000'}
        
        session = MagicMock()
        def get_response(url, params=None):
            if url == 'https://api.github.com/user':
                return mock_user_response
            elif url == 'https://api.github.com/user/repos' and params and params.get('per_page') == 100:
                return mock_response1
            elif url == 'https://api.github.com/user/repos?page=2':
                return mock_response2
            raise Exception(f"Unexpected request: {url} with params {params}")
        session.get.side_effect = get_response
        mock_session.return_value = session
        
        # Mock GitHub client initialization
        mock_user = MagicMock()
        mock_user.login = 'test-user'
        mock_github.return_value.get_user.return_value = mock_user
        
        service = GitHubService()
        results = service._get_all_pages('https://api.github.com/user/repos')
        
        # Verify the results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'repo1')
        self.assertEqual(results[1]['name'], 'repo2')
        
        # Verify the API calls
        calls = session.get.call_args_list
        self.assertEqual(len(calls), 3)  # Initial check + 2 page requests
        self.assertEqual(calls[1][0][0], 'https://api.github.com/user/repos')
        self.assertEqual(calls[1][1]['params']['per_page'], 100)
        self.assertEqual(calls[2][0][0], 'https://api.github.com/user/repos?page=2')

    @patch('repos.services.Github')
    @patch('repos.services.requests.Session')
    def test_rate_limit_handling(self, mock_session, mock_github):
        # Test rate limit handling
        # Mock GitHub client initialization
        mock_user = MagicMock()
        mock_user.login = 'test-user'
        mock_github.return_value.get_user.return_value = mock_user
        
        # Mock initial user response
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.headers = {'X-RateLimit-Remaining': '5000'}
        
        # Mock rate-limited response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(timezone.now().timestamp()) + 3600)
        }
        mock_response.json.return_value = []  # Should not be called
        
        session = MagicMock()
        def get_response(url, params=None):
            if url == 'https://api.github.com/user':
                return mock_user_response
            elif url == 'https://api.github.com/user/repos' and params and params.get('per_page') == 100:
                return mock_response
            raise Exception(f"Unexpected request: {url} with params {params}")
        session.get.side_effect = get_response
        mock_session.return_value = session
        
        service = GitHubService()
        with self.assertRaises(Exception) as context:
            service._get_all_pages('https://api.github.com/user/repos')
        
        self.assertIn('rate limit', str(context.exception).lower())
        self.assertEqual(session.get.call_count, 2)  # Initial check + 1 page request
        self.assertFalse(mock_response.json.called)  # Verify json() was not called

    @patch('repos.services.Github')
    @patch('repos.services.requests.Session')
    def test_sync_repositories(self, mock_session, mock_github):
        # Test repository synchronization
        # Mock API responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 3,
                'name': 'test-repo-3',
                'full_name': 'user/test-repo-3',
                'html_url': 'https://github.com/user/test-repo-3',
                'private': False,
                'fork': False,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z',
                'pushed_at': '2024-01-01T00:00:00Z',
                'size': 3000,
                'language': 'Python',
                'default_branch': 'main',
                'owner': {'login': 'user', 'type': 'User'},
                'description': 'Test repo'
            }
        ]
        mock_response.headers = {'X-RateLimit-Remaining': '4999'}
        mock_session.return_value.get.return_value = mock_response
        
        # Mock GitHub client
        mock_user = MagicMock()
        mock_user.login = 'test-user'
        mock_github.return_value.get_user.return_value = mock_user
        
        mock_repo = MagicMock()
        mock_branch = MagicMock()
        mock_branch.name = 'main'
        mock_repo.get_branches.return_value = [mock_branch]
        mock_github.return_value.get_repo.return_value = mock_repo
        
        service = GitHubService()
        repos = service.sync_repositories()
        
        # Verify results
        self.assertTrue(len(repos) > 0)
        new_repo = Repository.objects.get(github_id=3)
        self.assertEqual(new_repo.name, 'test-repo-3')
        self.assertEqual(new_repo.language, 'Python')

    @patch('repos.services.Github')
    @patch('repos.services.requests.Session')
    def test_sync_branches(self, mock_session, mock_github):
        # Test branch synchronization
        # Mock GitHub client initialization
        mock_user = MagicMock()
        mock_user.login = 'test-user'
        mock_github.return_value.get_user.return_value = mock_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        
        # Mock repository and branches
        mock_repo = MagicMock()
        
        # Mock main branch
        mock_branch1 = MagicMock()
        mock_branch1.name = 'main'
        mock_commit1 = MagicMock()
        mock_commit1.sha = 'abc123'
        mock_commit1.commit = MagicMock()
        mock_commit1.commit.message = 'Initial commit'
        mock_branch1.commit = mock_commit1
        
        # Mock develop branch
        mock_branch2 = MagicMock()
        mock_branch2.name = 'develop'
        mock_commit2 = MagicMock()
        mock_commit2.sha = 'def456'
        mock_commit2.commit = MagicMock()
        mock_commit2.commit.message = 'Development commit'
        mock_branch2.commit = mock_commit2
        
        # Set up mock repo
        mock_repo.get_branches.return_value = [mock_branch1, mock_branch2]
        mock_repo.default_branch = 'main'
        
        service = GitHubService()
        service._sync_branches(self.repo1, mock_repo)
        
        # Verify branches were created
        branches = Branch.objects.filter(repository=self.repo1)
        self.assertEqual(branches.count(), 2)
        
        main_branch = branches.get(name='main')
        self.assertEqual(main_branch.last_commit_sha, 'abc123')
        self.assertEqual(main_branch.last_commit_message, 'Initial commit')
        self.assertTrue(main_branch.is_default)
        
        develop_branch = branches.get(name='develop')
        self.assertEqual(develop_branch.last_commit_sha, 'def456')
        self.assertEqual(develop_branch.last_commit_message, 'Development commit')
        self.assertFalse(develop_branch.is_default)
