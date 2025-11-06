"""
WSGI config for climbing_system project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climbing_system.settings')

application = get_wsgi_application()








