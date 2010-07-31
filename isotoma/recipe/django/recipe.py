from random import choice
import os
import sys
import subprocess
import urllib2
import shutil
import logging
import re

from zc.buildout import UserError
import zc.recipe.egg
import setuptools

script_template = {
    'wsgi': '''

%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

application = %(module_name)s.%(attrs)s(%(arguments)s)
''',
    'fcgi': '''

%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

%(module_name)s.%(attrs)s(%(arguments)s)
'''
}

settings_template = """
# $Id$

# Base settings
__author__ = 'Forename Surname <forename@isotoma.com>'
__docformat__ = 'restructuredtext en'
__version__ = '$Revision$'[11:-2]

import logging
import os
import platform
import sys

from django.utils.importlib import import_module

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SERVE_STATIC = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

SYSTEM_EMAIL = "noreply@isotoma.com"

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Calculated site root
PATH_SITE_ROOT = os.path.normpath(os.path.dirname(__file__))

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PATH_SITE_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://localhost:8000/static'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '%(secret)s'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATE_DIRS = (
    os.path.join(PATH_SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    %(app_fqn)s
)

ROOT_URLCONF = '%(project_name)s.urls'

# Override with environment specific settings
try:
    from local_settings import *
except ImportError:
    pass



"""

production_settings_template = """
from settings import *

DEBUG = False
SERVE_STATIC = False
MEDIA_URL = ''
"""

urls_template = """
# $Id$

# Urls
__author__ = 'Forename Surname <forename@isotoma.com>'
__docformat__ = 'restructuredtext en'
__version__ = '$Revision$'[11:-2]

from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseNotFound, HttpResponseServerError
from django.template.loader import render_to_string

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
        
    # Prevent search engine spiders from generating 404s when looking for a 
    # robots.txt. Obviously remove these if using actual files
    # (This way is less efficient than doing it via server config. 
    # Keeps it in-app though.)
    (r'^robots\.txt$', lambda r: HttpResponse("", mimetype="text/plain")),
	
    # Redirect a request for favicon.ico from the virtual root to where it 
    # actually is. Many user agents (RIM based blackberry browsers, old 
    # versions of IE etc) lazily look in the root first, raising a 404
    (r'^favicon\.ico$', lambda r: HttpResponseRedirect('/static/images/favicon.ico')),
)

# Serve static content through Django.
# (This way is less efficient than having the web server do it and unless 
# there is a decent caching layer, SERVE_STATIC should be False for production)
if settings.SERVE_STATIC:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT }),
    )

# We can also redirect to templates wherever we like here.
handler404 = '%s.return_404' % (settings.ROOT_URLCONF,)
handler500 = '%s.return_500' % (settings.ROOT_URLCONF,)

def return_404(request):
    return HttpResponseNotFound(render_to_string("errors/404.html"))

def return_500(request):
    return HttpResponseServerError(render_to_string("errors/500.html"))

"""

class Recipe(object):
    def __init__(self, buildout, name, options):
        self.log = logging.getLogger(name)
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)

        self.buildout, self.name, self.options = buildout, name, options
        options['location'] = os.path.join(
            buildout['buildout']['parts-directory'], name)
        options['bin-directory'] = buildout['buildout']['bin-directory']

        options.setdefault('project', 'project')
        options.setdefault('settings', 'development')

        options.setdefault('urlconf', options['project'] + '.urls')
        options.setdefault(
            'media_root',
            "os.path.join(os.path.dirname(__file__), 'media')")
        # Set this so the rest of the recipe can expect the values to be
        # there. We need to make sure that both pythonpath and extra-paths are
        # set for BBB.
        if 'extra-paths' in options:
            options['pythonpath'] = options['extra-paths']
        else:
            options.setdefault('extra-paths', options.get('pythonpath', ''))

        # Usefull when using archived versions
        buildout['buildout'].setdefault(
            'download-cache',
            os.path.join(buildout['buildout']['directory'],
                         'downloads'))

        # mod_wsgi support script
        options.setdefault('wsgi', 'false')
        options.setdefault('fcgi', 'false')
        options.setdefault('wsgilog', '')
        options.setdefault('logfile', '')

        # only try to download stuff if we aren't asked to install from cache
        self.install_from_cache = self.buildout['buildout'].get(
            'install-from-cache', '').strip() == 'true'


    def install(self):
        location = self.options['location']
        base_dir = self.buildout['buildout']['directory']

        # the directory to hold the project
        project_dir = os.path.join(base_dir, os.path.join('src', self.options['project']))

        download_dir = self.buildout['buildout']['download-cache']
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        version = self.options['version']
        # Remove a pre-existing installation if it is there
        if os.path.exists(location):
            shutil.rmtree(location)

        if self.is_svn_url(version):
            self.install_svn_version(version, download_dir, location,
                                     self.install_from_cache)
        else:
            tarball = self.get_release(version, download_dir)
            # Extract and put the dir in its proper place
            self.install_release(version, download_dir, tarball, location)

        
        self.options['setup'] = location
        development = zc.recipe.egg.Develop(self.buildout,
                                            self.options['recipe'],
                                            self.options)
        development.install()
        del self.options['setup']

        extra_paths = self.get_extra_paths()
        requirements, ws = self.egg.working_set(['djangorecipe'])

        script_paths = []
        
        # add the installed django to the paths
        sys.path.append(location)
        
        # if we don't have a directory for a project,
        # we will probably need to create one
        # Make it so.
        if not os.path.exists(project_dir):
            self.create_project(os.path.join(base_dir, 'src'))

        # Create the Django management script
        script_paths.extend(self.create_manage_script(extra_paths, ws))
        
        # Create the Django admin script
        script_paths.extend(self.create_admin_script(extra_paths, ws))

        # Create the test runner
        script_paths.extend(self.create_test_runner(extra_paths, ws))

        # Make the wsgi and fastcgi scripts if enabled
        script_paths.extend(self.make_scripts(extra_paths, ws))
        
        

        return script_paths + [location]

    def install_svn_version(self, version, download_dir, location,
                            install_from_cache):
        svn_url = self.version_to_svn(version)
        download_location = os.path.join(
            download_dir, 'django-' +
            self.version_to_download_suffix(version))
        if not install_from_cache:
            if os.path.exists(download_location):
                if self.svn_update(download_location, version):
                    raise UserError(
                        "Failed to update Django; %s. "
                        "Please check your internet connection." % (
                            download_location))
            else:
                self.log.info("Checking out Django from svn: %s" % svn_url)
                cmd = 'svn co %s %s' % (svn_url, download_location)
                if not self.buildout['buildout'].get('verbosity'):
                    cmd += ' -q'
                if self.command(cmd):
                    raise UserError("Failed to checkout Django. "
                                    "Please check your internet connection.")
        else:
            self.log.info("Installing Django from cache: " + download_location)

        shutil.copytree(download_location, location)


    def install_release(self, version, download_dir, tarball, destination):
        extraction_dir = os.path.join(download_dir, 'django-archive')
        setuptools.archive_util.unpack_archive(tarball, extraction_dir)
        # Lookup the resulting extraction dir instead of guessing it
        # (Django releases have a tendency not to be consistend here)
        untarred_dir = os.path.join(extraction_dir,
                                    os.listdir(extraction_dir)[0])
        shutil.move(untarred_dir, destination)
        shutil.rmtree(extraction_dir)

    def get_release(self, version, download_dir):
        tarball = os.path.join(download_dir, 'django-%s.tar.gz' % version)

        # Only download when we don't yet have an archive
        if not os.path.exists(tarball):
            if self.options.has_key('download_url'):
                download_url = self.options['download_url']
                self.log.info("Downloading Django from: %s" % (
                    download_url))
            else:
                download_url = 'http://www.djangoproject.com/download/%s/tarball/'
                self.log.info("Downloading Django from: %s" % (
                    download_url % version))
                download_url = download_url % version

            tarball_f = open(tarball, 'wb')
            f = urllib2.urlopen(download_url)
            tarball_f.write(f.read())
            tarball_f.close()
            f.close()
        return tarball

    def create_manage_script(self, extra_paths, ws):
        project = self.options.get('projectegg', self.options['project'])
        return zc.buildout.easy_install.scripts(
            [(self.options.get('control-script', self.name),
              'djangorecipe.manage', 'main')],
            ws, self.options['executable'], self.options['bin-directory'],
            extra_paths = extra_paths,
            arguments= "'%s.%s'" % (project,
                                    self.options['settings']))

    def create_admin_script(self, extra_paths, ws):
        project = self.options.get('projectegg', self.options['project'])
        return zc.buildout.easy_install.scripts(
            [(self.options.get('admin-script', self.name + "-admin"),
              'djangorecipe.admin', 'main')],
            ws, self.options['executable'], self.options['bin-directory'],
            extra_paths = extra_paths)

    def create_test_runner(self, extra_paths, working_set):
        apps = self.options.get('test', '').split()
        # Only create the testrunner if the user requests it
        if apps:
            return zc.buildout.easy_install.scripts(
                [(self.options.get('testrunner', 'test'),
                  'djangorecipe.test', 'main')],
                working_set, self.options['executable'],
                self.options['bin-directory'],
                extra_paths = extra_paths,
                arguments= "'%s.%s', %s" % (
                    self.options['project'],
                    self.options['settings'],
                    ', '.join(["'%s'" % app for app in apps])))
        else:
            return []


    def create_project(self, source_dir):
        # create the project dir
        #os.makedirs(project_dir)
        os.makedirs(source_dir)
        
        existing_path = os.getcwd()
        os.chdir(source_dir)
        
        project_dir = os.path.join(source_dir, self.options['project'])

        # use the inbuilt tools to create the project
        from django.core.management.commands import startproject, startapp
        start_project = startproject.Command()
        start_project.handle_label(self.options['project'])
        
        # start the apps that are listed in the buildout
        apps = self.options.get('apps', '').split()
        start_app = startapp.Command()
        for app in apps:
            start_app.handle_label(app, project_dir)
        
        template_vars = {'secret': self.generate_secret(),
                        'app_fqn': self.generate_installed_apps(),
                        'project_name': self.options['project']}
        
        # Create the settings files for the project
        self.create_file(os.path.join(project_dir, 'settings.py'), settings_template, template_vars, overwrite = True)
        self.create_file(os.path.join(project_dir, 'production.py'), production_settings_template, template_vars)
        
        # Create the static directory
        os.makedirs(os.path.join(project_dir, 'static'))
        # Create the templates directory
        os.makedirs(os.path.join(project_dir, 'templates'))
        
        # Create the urls file
        self.create_file(os.path.join(project_dir, 'urls.py'), urls_template, overwrite = True, format = False)
        
        os.chdir(existing_path)

    def make_scripts(self, extra_paths, ws):
        scripts = []
        _script_template = zc.buildout.easy_install.script_template
        for protocol in ('wsgi', 'fcgi'):
            zc.buildout.easy_install.script_template = \
                zc.buildout.easy_install.script_header + \
                    script_template[protocol]
            if self.options.get(protocol, '').lower() == 'true':
                project = self.options.get('projectegg',
                                           self.options['project'])
                scripts.extend(
                    zc.buildout.easy_install.scripts(
                        [('%s.%s' % (self.options.get('control-script',
                                                      self.name),
                                     protocol),
                          'isotoma.recipe.django.%s' % protocol, 'main')],
                        ws,
                        self.options['executable'],
                        self.options['bin-directory'],
                        extra_paths=extra_paths,
                        arguments= "'%s.%s', logfile='%s'" % (
                            project, self.options['settings'],
                            self.options.get('logfile'))))
        zc.buildout.easy_install.script_template = _script_template
        return scripts

    def is_svn_url(self, version):
        # Search if there is http/https/svn or svn+[a tunnel identifier] in the
        # url or if the trunk marker is used, all indicating the use of svn
        svn_version_search = re.compile(
            r'^(http|https|svn|svn\+[a-zA-Z-_]+)://|^(trunk)$').search(version)
        return svn_version_search is not None

    def version_to_svn(self, version):
        if version == 'trunk':
            return 'http://code.djangoproject.com/svn/django/trunk/'
        else:
            return version

    def version_to_download_suffix(self, version):
        if version == 'trunk':
            return 'svn'
        return [p for p in version.split('/') if p][-1]

    def svn_update(self, path, version):
        command = 'svn up'
        revision_search = re.compile(r'@([0-9]*)$').search(
            self.options['version'])

        if revision_search is not None:
            command += ' -r ' + revision_search.group(1)
        self.log.info("Updating Django from svn")
        if not self.buildout['buildout'].get('verbosity'):
            command += ' -q'
        return self.command(command, cwd=path)

    def get_extra_paths(self):
        extra_paths = [self.options['location'],
                       self.buildout['buildout']['directory']
                       ]

        # Add the project that we are creating
        if self.options.has_key('project'):
            project_src_path = os.path.join(self.buildout['buildout']['cwd'], 'src')
            extra_paths.append(project_src_path)
        
        # Add libraries found by a site .pth files to our extra-paths.
        if 'pth-files' in self.options:
            import site
            for pth_file in self.options['pth-files'].splitlines():
                pth_libs = site.addsitedir(pth_file, set())
                if not pth_libs:
                    self.log.warning(
                        "No site *.pth libraries found for pth_file=%s" % (
                         pth_file,))
                else:
                    self.log.info("Adding *.pth libraries=%s" % pth_libs)
                    self.options['extra-paths'] += '\n' + '\n'.join(pth_libs)

        pythonpath = [p.replace('/', os.path.sep) for p in
                      self.options['extra-paths'].splitlines() if p.strip()]

        extra_paths.extend(pythonpath)
        return extra_paths

    def update(self):
        newest = self.buildout['buildout'].get('newest') != 'false'
        if newest and not self.install_from_cache and \
                self.is_svn_url(self.options['version']):
            self.svn_update(self.options['location'], self.options['version'])

        extra_paths = self.get_extra_paths()
        requirements, ws = self.egg.working_set(['djangorecipe'])
        # Create the Django management script
        self.create_manage_script(extra_paths, ws)
        
        # Create the Django admin script
        self.create_admin_script(extra_paths, ws)

        # Create the test runner
        self.create_test_runner(extra_paths, ws)

        # Make the wsgi and fastcgi scripts if enabled
        self.make_scripts(extra_paths, ws)

    def command(self, cmd, **kwargs):
        output = subprocess.PIPE
        if self.buildout['buildout'].get('verbosity'):
            output = None
        command = subprocess.Popen(
            cmd, shell=True, stdout=output, **kwargs)
        return command.wait()

    def create_file(self, file, template, options = {}, overwrite = False, format = True):
        if not overwrite and os.path.exists(file):
            return

        f = open(file, 'w')
        if format:
            f.write(template % options)
        else:
            f.write(template)
        f.close()
        
    def append_file(self, file, template, options):
        """ Append a template to an existing file, such as those created in the project creation """
        f = open(file, 'a')
        f.write(template % options)
        f.close()

    def generate_secret(self):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join([choice(chars) for i in range(50)])
        
    def generate_installed_apps(self):
        apps = self.options['apps'].split()
        app_list = []
        for app in apps:
            app_list.append('\'' + self.options['project'] + '.' + app + '\'')
            
        return ','.join(app_list)
