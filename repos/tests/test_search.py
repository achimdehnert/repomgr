from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from repos.models import Repository
from repos.forms import RepositorySearchForm

class RepositorySearchTests(TestCase):
    def setUp(self):
        # Create a test user and log them in
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # Create test repositories
        self.repo1 = Repository.objects.create(
            github_id=1,
            name="django-project",
            full_name="user/django-project",
            description="A Django web application",
            url="https://github.com/user/django-project",
            private=False,
            fork=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            pushed_at=timezone.now(),
            size=1000,
            language="Python",
            default_branch="main"
        )

        self.repo2 = Repository.objects.create(
            github_id=2,
            name="react-app",
            full_name="org/react-app",
            description="A React application",
            url="https://github.com/org/react-app",
            private=True,
            fork=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            pushed_at=timezone.now(),
            size=2000,
            language="JavaScript",
            default_branch="main",
            organization="TestOrg"
        )

        self.repo3 = Repository.objects.create(
            github_id=3,
            name="python-utils",
            full_name="user/python-utils",
            description="Python utility functions",
            url="https://github.com/user/python-utils",
            private=False,
            fork=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            pushed_at=timezone.now(),
            size=500,
            language="Python",
            default_branch="main"
        )

    def test_repository_search_by_name(self):
        """Test searching repositories by name"""
        results = Repository.search("django")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.repo1)

    def test_repository_search_by_description(self):
        """Test searching repositories by description"""
        results = Repository.search("utility")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.repo3)

    def test_repository_search_by_language(self):
        """Test searching repositories by language"""
        results = Repository.search("Python")
        self.assertEqual(results.count(), 2)
        self.assertIn(self.repo1, results)
        self.assertIn(self.repo3, results)

    def test_repository_search_by_organization(self):
        """Test searching repositories by organization"""
        results = Repository.search("TestOrg")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.repo2)

    def test_repository_search_case_insensitive(self):
        """Test that search is case insensitive"""
        results = Repository.search("PYTHON")
        self.assertEqual(results.count(), 2)
        self.assertIn(self.repo1, results)
        self.assertIn(self.repo3, results)

    def test_repository_search_no_results(self):
        """Test search with no matching results"""
        results = Repository.search("nonexistent")
        self.assertEqual(results.count(), 0)

    def test_search_form_valid(self):
        """Test search form with valid data"""
        form = RepositorySearchForm(data={'query': 'python'})
        self.assertTrue(form.is_valid())

    def test_search_form_empty(self):
        """Test search form with empty query"""
        form = RepositorySearchForm(data={'query': ''})
        self.assertTrue(form.is_valid())

    def test_repository_list_view_with_search(self):
        """Test repository list view with search parameter"""
        response = self.client.get(reverse('repos:repository_list'), {'query': 'python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'django-project')
        self.assertContains(response, 'python-utils')
        self.assertNotContains(response, 'react-app')

    def test_repository_list_view_sorting(self):
        """Test repository list view with sorting parameter"""
        # Test sorting by name
        response = self.client.get(reverse('repos:repository_list'), {'sort': 'name'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check if repositories appear in alphabetical order
        django_pos = content.find('django-project')
        python_pos = content.find('python-utils')
        react_pos = content.find('react-app')
        self.assertTrue(django_pos < python_pos)
        self.assertTrue(python_pos < react_pos)

    def test_repository_list_view_no_query(self):
        """Test repository list view without search parameter"""
        response = self.client.get(reverse('repos:repository_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'django-project')
        self.assertContains(response, 'react-app')
        self.assertContains(response, 'python-utils')
