import os

# General
DEBUG = True
TEMPLATE_DEBUG = DEBUG
ADMINS = []
MANAGERS = ADMINS
SITE_ID = 1
SECRET_KEY = ')ac&4$g@r)*i*()-fi+h9s42^ov8!3ij8^-c0a1tg0=-_(ow&b'

# Reusable values
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_NAME = 'test_project'

# Default sqlite3 db
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Media
MEDIA_URL = '/static/'
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'static')
ADMIN_MEDIA_PREFIX = '/admin/media/'

#Interlocalination
TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-GB'
USE_I18N = False
USE_L10N = True

# URLs
ROOT_URLCONF = '%s.urls' % PROJECT_NAME

# Pluggable bits
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, 'templates'),
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
]

# Logging
LOGFILE = os.path.join(PROJECT_ROOT, 'logs/%s.log' % PROJECT_NAME)

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(process)d %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
    },
    'handlers': {
        'log_file': {
            'level': 'INFO',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': LOGFILE,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'django.request': {
            'handlers': ['log_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        PROJECT_NAME: {
            'handlers': ['log_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
