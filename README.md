# RepOMgr: GitHub Repository Management Tool

## Overview
A Django-based web application for managing GitHub repositories efficiently. RepOMgr helps you track, synchronize, and manage your GitHub repositories through an intuitive web interface.

## Features
- Browse and filter your GitHub repositories
- Import repositories from GitHub with pagination support
- View repository details including branches and commit history
- Support for private repositories and organization repositories
- Rate limit handling and efficient API usage
- Beautiful and responsive web interface

## Prerequisites
- Python 3.8+
- GitHub Personal Access Token with appropriate scopes:
  - `repo` (for private repositories)
  - `read:org` (for organization repositories)
  - `read:user` (for user information)

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/repomgr.git
cd repomgr
```

2. Create and activate virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

## Configuration

### GitHub Token
Set your GitHub Personal Access Token:

#### Option 1: Environment Variable
```bash
export GITHUB_ACCESS_TOKEN=your_github_token  # Unix/macOS
set GITHUB_ACCESS_TOKEN=your_github_token     # Windows
```

#### Option 2: .env File
Create a `.env` file in the project root:
```
GITHUB_ACCESS_TOKEN=your_github_token
```

## Usage

### Start the Development Server
```bash
python manage.py migrate  # Set up the database
python manage.py createsuperuser  # Create an admin user
python manage.py runserver  # Start the server
```

Then visit http://localhost:8000 in your browser.

### Import Repositories
1. Navigate to the Import page
2. Enter your GitHub username
3. Choose import options (private repos, organization repos)
4. Click Import to start the synchronization

### View and Filter Repositories
- Use the repository list page to view all synchronized repositories
- Filter repositories by name, language, or type
- Click on a repository to view detailed information

## Development

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific test modules
python manage.py test repos.tests.test_services repos.tests.test_views

# Run with verbosity
python manage.py test -v 2
```

### Test Coverage
The project includes comprehensive tests for:
- GitHub API integration with proper pagination
- Rate limit handling and error recovery
- Repository and branch synchronization
- Web interface functionality

### Code Organization
- `repos/`: Main application code
  - `services.py`: GitHub API integration
  - `views.py`: Web interface views
  - `models.py`: Database models
  - `tests/`: Test modules
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and other static files

## Contributing
Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
