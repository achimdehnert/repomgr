# RepOMgr: GitHub Repository Management Tool

## Overview
A CLI tool to manage GitHub repositories efficiently.

## Features
- List repositories for a user
- Create new repositories
- Manage repository settings

## Prerequisites
- Python 3.8+
- GitHub Personal Access Token

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
```

## Configuration

### GitHub Token
Set your GitHub Personal Access Token:

#### Option 1: Environment Variable
```bash
export GITHUB_TOKEN=your_github_token  # Unix/macOS
set GITHUB_TOKEN=your_github_token  # Windows
```

#### Option 2: .env File
Create a `.env` file in the project root:
```
GITHUB_TOKEN=your_github_token
```

## Usage

### List Repositories
```bash
python -m src.cli list-repos [--username YOUR_USERNAME]
```

### Create Repository
```bash
python -m src.cli create-repo REPO_NAME [--description DESCRIPTION] [--private]
```

## Development
- Run tests: `pytest`
- Code formatting: `black .`
- Type checking: `mypy src`

## Contributing
Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.
