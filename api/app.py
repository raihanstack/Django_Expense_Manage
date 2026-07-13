import os
from django.core.wsgi import get_wsgi_application

# Ensure settings module is set for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Vercel expects a WSGI callable named `app`
app = get_wsgi_application()
# alias for compatibility with older naming
handler = app
