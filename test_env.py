import os

def load_env():
    with open('.env') as f:
        content = f.read()
        print("Content of .env file:")
        print(content)
        print("\nTrying to load variables...")
        for line in content.splitlines():
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

load_env()
token = os.environ.get('GITHUB_ACCESS_TOKEN')
print(f"\nGitHub token from environment: {'Not found' if not token else f'Found (starts with {token[:4]})'}")
