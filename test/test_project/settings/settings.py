from .base import *

INSTALLED_APPS += [
    # Your apps go here.
]
# development settings

try:
    from local_settings import *
except ImportError:
    pass
