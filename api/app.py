import os
from django.core.wsgi import get_wsgi_application

# Ensure settings module is set for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Vercel expects a variable named `handler` (or `app`) to expose the WSGI app
handler = get_wsgi_application()
