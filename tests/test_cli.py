import pytest
from src.cli import RepoManager


def test_repo_manager_initialization():
    """
    Test RepoManager initialization with environment variable
    """
    import os

    # Ensure GitHub token is set
    assert (
        os.getenv("GITHUB_TOKEN") is not None
    ), "GitHub token must be set in environment"

    # Test initialization
    try:
        manager = RepoManager()
        assert manager.github_token is not None
    except ValueError:
        pytest.fail("Failed to initialize RepoManager")
