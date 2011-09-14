import logging
import os
import sys
from random import choice

import zc.recipe.egg
from zc.buildout import easy_install

from jinja2 import Template, Environment, PackageLoader

class Recipe(zc.recipe.egg.Egg):
    """ A buildout recipe to install django, and configure a project """
    
    def __init__(self, buildout, name, options):
        """ Set up the options and paths that we will use later in the recipe """
        super(Recipe, self).__init__(buildout, name, options)

        # set up some bits for the buildout to user
        self.log = logging.getLogger(name)

        # where the control scripts are going to live
        self.options["bin-directory"] = buildout["buildout"]["bin-directory"]

        # the name of the project manage.py that is created in bin-directory
        self.options.setdefault("control-script", "django")
        # which settings file to use
        self.options.setdefault("settings", "settings")
        # whether to generate a wsgi file
        self.options.setdefault("wsgi", "false")

        # template environment
        self.template_environment = Environment(
            loader=PackageLoader("isotoma.recipe.django", "templates")
        )

        # get the extra paths that we might need
        if self.options.has_key("extra-paths"):
            self.extra_paths = [
                path.strip() for path in self.options["extra-paths"].split("\n")
                if path.strip()
            ]
        else:
            self.extra_paths = []

    def install(self):
        """ Create and set up the project """

        # the base directory for the installed files
        base_dir = self.buildout["buildout"]["directory"] 
        src_dir = os.path.join(base_dir, "src")
        project_dir = os.path.join("src", self.options["project"])

        # install the control scripts for django
        self.install_scripts(src_dir, project_dir)

        return self.options.created()


    def install_scripts(self, source_dir, project_dir):
        """ Install the control scripts that we need """

        # use the working set to correctly create the scripts with the correct
        # python path
        ws = self.working_set(extra=('isotoma.recipe.django',))[1]

        easy_install.scripts(
            [(
                "django-admin",
                "django.core.management",
                "execute_from_command_line"
            )],
            ws,
            self.options['executable'],
            self.options['bin-directory'],
            extra_paths = self.extra_paths
        )

        # this is a bit nasty
        # we need to add the project to the working set so we can import from it
        # so we're adding it's directory as an extra_path, as egg installing it
        # doesn't seem to be much success

        # install the project script ("manage.py")
        easy_install.scripts(
            [(
                self.options["control-script"],
                "django.core.management",
                "execute_manager"
            )],
            ws,
            self.options['executable'],
            self.options['bin-directory'],
            arguments="settings",
            initialization="import %s.%s as settings" % (
                self.options["project"],
                self.options["settings"]
            ),
            extra_paths = self.extra_paths
        )

        # install the wsgi script if required
        if self.options["wsgi"].lower() == "true":
            # the name of the wsgi script that will end up in bin-directory
            wsgi_name = "%s.%s" % (self.options["control-script"], "wsgi")
            # install the wsgi script
            # we need to reset the template, as we need a custom script, rather
            # than the standard buildout one

            # store the old one
            _script_template = easy_install.script_template

            # set our new template
            easy_install.script_template = easy_install.script_header + open(
                os.path.join(os.path.dirname(__file__), "templates/wsgi.tmpl")
            ).read() 

            project_real_path = os.path.realpath(project_dir)

            easy_install.scripts(
                [(
                    wsgi_name,
                    "isotoma.recipe.django.wsgi",
                    "main"
                )],
                ws,
                self.options['executable'],
                self.options['bin-directory'],
                arguments="settings",
                initialization="import %s.%s as settings" % (
                    self.options["project"],
                    self.options["settings"]
                ),
                extra_paths = [project_real_path] + self.extra_paths
            )
            zc.buildout.easy_install.script_template = _script_template

        # add the created scripts to the buildout installed stuff, so they get removed correctly
        self.options.created(
            os.path.join(self.options['bin-directory'], "django-admin")
        )

