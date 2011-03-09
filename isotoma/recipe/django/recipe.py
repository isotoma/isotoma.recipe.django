import logging
import os
import sys
from random import choice

import zc.recipe.egg
from zc.buildout import easy_install

from jinja2 import Template, Environment, PackageLoader

class Recipe(object):
    """ A buildout recipe to install django, and configure a project """
    
    def __init__(self, buildout, name, options):
        """ Set up the options and paths that we will use later in the recipe """
        
        # set up some bits for the buildout to user
        self.log = logging.getLogger(name)
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)
        
        # set the options that we've been passed so we can get them when we install
        self.buildout = buildout
        self.name = name
        self.options = options        
        
        # set the paths that we'll need
        self.options['bin-directory'] = buildout['buildout']['bin-directory'] # where the control scripts are going to live
        
        # set any default options that we might need later in the recipe
        self.options.setdefault('control-script', 'django')  # the name of the project manage.py that is created in bin-directory
        self.options.setdefault('settings', 'settings') # which settings file to use
        self.options.setdefault('wsgi', 'false') # whether to generate a wsgi file
        
        # template environment
        self.template_environment = Environment(loader=PackageLoader('isotoma.recipe.django', 'templates'))
        
    def install(self):
        """ Create and set up the project """
        
        # work out where we're creating the project
        base_dir = self.buildout['buildout']['directory'] # the base directory for the installed files
        src_dir = os.path.join(base_dir, 'src')
        project_dir = os.path.join('src', self.options['project'])
            
        # install the control scripts for django
        self.install_scripts(src_dir, project_dir)
        
        return self.options.created()
    
    def install_scripts(self, source_dir, project_dir):
        """ Install the control scripts that we need """
        
        # get the paths that we need
        path = self.buildout["buildout"]["bin-directory"]
        egg_paths = [
            self.buildout["buildout"]["develop-eggs-directory"],
            self.buildout["buildout"]["eggs-directory"],
            ]
        
        # calculate the eggs that we need to install
        eggs_to_install = ["isotoma.recipe.django"]
        for egg in self.options['eggs'].split('\n'):
            e = egg.strip()
            if not e == "":
                eggs_to_install.append(e)
        
        # use the working set to correctly create the scripts with the correct python path
        ws = easy_install.working_set(eggs_to_install, self.buildout['buildout']['executable'] ,egg_paths)
        easy_install.scripts([('django-admin', "django.core.management", "execute_from_command_line")], ws, sys.executable, path)
        
        # this is a bit nasty
        # we need to add the project to the working set so we can import from it
        # so we're adding it's directory as an extra_path, as egg installing it doesn't seem to be much success
        # install the project script ('manage.py')
        easy_install.scripts([(self.options['control-script'], 'django.core.management', 'execute_manager')], ws, sys.executable, path, arguments='settings', initialization="import %s.%s as settings" % (self.options['project'], self.options['settings']))
        
        # install the wsgi script if required
        if self.options['wsgi'].lower() == 'true':
            wsgi_name = '%s.%s' % (self.options['control-script'], 'wsgi') # the name of the wsgi script that will end up in bin-directory
            # instal the wsgi script
            # we need to reset the template, as we need a custom script, rather than the standard buildout one
            _script_template = zc.buildout.easy_install.script_template # store the old one
            zc.buildout.easy_install.script_template = zc.buildout.easy_install.script_header + open(os.path.join(os.path.dirname(__file__), 'templates/wsgi.tmpl')).read() # set our new template
            easy_install.scripts([(wsgi_name, 'isotoma.recipe.django.wsgi', 'main')], ws, sys.executable, path, arguments='settings', initialization="import %s as settings" % (self.options['settings']), extra_paths = [os.path.realpath(project_dir)])
            zc.buildout.easy_install.script_template = _script_template
        
        # add the created scripts to the buildout installed stuff, so they get removed correctly
        self.options.created(os.path.join(path, 'django-admin'))
        