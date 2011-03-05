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
        
    def create_project(self, src_dir, project_name):
        """ Create the django project in the correct directory 

        Arguments:
        src_dir - Directory to create the project in (it will create a containing directory for the project)
        project_name - Name of the project to create
        app_list - List of the apps to create in the project
        
        Returns a path to the created project directory
        """
        
        # check if the project already exists
        project_dir = os.path.join(src_dir, project_name)
        if os.path.exists(project_dir):
            self.log.info("Project %s already exists" % project_name)
            return project_dir, False
        
        self.log.info("Creating project: %s in %s" % (project_name, src_dir))
        
        # at this point, the project directory should not exist, so create it
        if not os.path.exists(src_dir): os.makedirs(src_dir)
        
        # now we need to be in the project directory, as the project creation tools cannot accept a dir, they use cwd
        existing_path = os.getcwd()
        os.chdir(src_dir)
        
        # we're now in the project directory, time to create it.
        from django.core.management.commands import startproject
        project = startproject.Command()
        project.handle_label(project_name)
        
        # now we remove the settings.py, as we're going to recreate it
        self.log.info("Removing default settings.py from project")
        os.remove(os.path.join(project_dir, 'settings.py'))
        
        # change back to the old directory, so we don't screw anyone else up
        os.chdir(existing_path)
        
        self.log.info("Done creating project")
        
        return src_dir, True
    
    def create_app(self, project_dir, app_name):
        """ Create an app in the project
        
        Arguments:
        project_dir - the directory of the project
        app_name - name of the app that is created
        
        Returns a path to the created app directory
        """
        # we need this to return it
        app_dir = os.path.join(project_dir, app_name)
        
        # if the app already exists, don't create a new one
        if os.path.exists(app_dir):
            self.log.info("App %s already exists at %s" % (app_name, app_dir))
            return app_dir
        
        # if we get here, we need a new app
        self.log.info("Creating app: %s in directory %s" % (app_name, project_dir))
        
        # now create the app
        from django.core.management.commands import startapp
        app = startapp.Command()
        app.handle_label(app_name, project_dir)
        
        self.log.info("Done creating app: %s" % app_name)
        
        return app_dir
    
    def create_project_files(self, project_dir, source_dir):
        """ Create the files that we need to run the project """
        
        # get the variables that we'll need for the templated files
        template_vars = {'secret': self._generate_secret(),
                'app_fqn': self._generate_installed_apps(),
                'project_name': self.options['project'],
                'server_email': self.options['server_email']}
        
        # create the various settings files that we'll need in a project
        self._create_file(os.path.join(project_dir, 'settings.py'), 'settings.tmpl', template_vars)
        self._create_file(os.path.join(project_dir, 'staging.py'), 'staging.tmpl', template_vars)
        self._create_file(os.path.join(project_dir, 'production.py'), 'production.tmpl', template_vars)
        
        # Create the static directory
        os.makedirs(os.path.join(project_dir, 'static'))
        # Create the templates directory
        os.makedirs(os.path.join(project_dir, 'templates'))
        
        # Create the urls file
        self._create_file(os.path.join(project_dir, 'urls.py'), 'urls.tmpl', template_vars)
        
        # Create the setup.py for transforming the project to an egg
        self._create_file(os.path.join(source_dir, 'setup.py'), 'setup.tmpl', template_vars)

    
    def _create_file(self, path, template, template_vars):
        """ Create a file on the filesystem
        
        Arguments:
        path - Path to the file to create
        template - Path to the template file
        template_vars - Variables to use in the template as a dictionary
        
        Returns a path to the created file"""
        
        self.log.info("Creating %s from template %s" % (path, template))
        
        # get the template from the loader (and directory)
        loaded_template = self.template_environment.get_template(template)
        
        # render the template given the data that we have
        rendered_template = loaded_template.render(template_vars)
        
        # save the rendered template where we were told to
        output_file = open(path, 'w')
        output_file.write(rendered_template)
        output_file.close()
        
        # return a path to the file
        return path
    
    def _generate_installed_apps(self):
        """ Create a string of the installed apps, from the buildout config """
        apps = self.options['apps'].split()
        app_list = []
        for app in apps:
            # is quoted as a string, so add quotes
            # is fqn, so needs project prepending
            app_list.append('\'' + self.options['project'] + '.' + app + '\'')

        if self.options.has_key('external_apps'):
            external_apps = self.options['external_apps'].split()
            for app in external_apps:
                # quote directly as a string
                app_list.append('\'' + app + '\'')
        return ',\n'.join(app_list)

    
    def _generate_secret(self):
        """ Generate a secret for the django settings file 
        
        Returns a 50 char string of the secret
        """
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join([choice(chars) for i in range(50)])

        