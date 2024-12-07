import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repomgr.settings')
django.setup()

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

try:
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    print("Superuser created successfully!")
    print("Username: admin")
    print("Password: admin123")
except IntegrityError:
    print("Superuser already exists!")
