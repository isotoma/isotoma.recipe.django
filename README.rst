=====================
isotoma.recipe.django
=====================

isotoma.recipe.django can be used to install Django. It's a whole lot like
djangorecipe except that Django is treated like a proper egg.

This recipe will make three scripts available in your bin/ directory:

bin/django
    This script works in exactly the same way as the manage.py script found in
    any typical django project; for example, you can run "bin/django syncdb".

bin/django-admin
    This script is the equivalent of the project-independent django-admin script
    available when django is installed using apt or easy_install.

bin/django.wsgi
    An optional script, created if the wsgi option is set to "true". This script
    is designed to be called by a web server.

The entire recipe assumes that your project is an egg and any apps contained
within your project *do not* need to be on sys.path and hence refer to each
other as::

    from yourproject.yourapp import models

Example
=======

::

    [buildout]
    parts = django
    versions = versions
    eggs =
        foo
        django-treebeard

    [django]
    recipe = isotoma.recipe.django
    project = foo
    settings = production
    wsgi = true
    eggs = ${buildout:eggs}
    
    [versions]
    Django = 1.3.1

Supported Options
=================

project
    The name of your django project, be it a develop egg or a regular one. Note
    that isotoma.recipe.django will *not* create a project for you if it does
    not exist.

settings
    The name of the settings file within your project to use, allowing you to
    create a settings.py containing development settings, and a production.py
    importing the development settings and overriding them where necessary.
    That way you just need to change this value from "settings" to "production".
    Defaults to "settings".

extra-paths
    Any extra paths to add to sys.path that should be made available to your
    project egg / develop-egg.

wsgi
    Defaults to false. If 'true', create a bin/django.wsgi script that can be
    added to a webserver configuration (using isotoma.recipe.apache for
    example - see below).

bin-on-path
    This feature appends the buildout bin/ directory to os.environ['PATH'] so
    that your django project will have access to the buildout executables.
    For example, this might be useful if you install sphinx in your buildout
    build and want access to the sphinx executables from within django (as is
    the case in the readthedocs.org project).

environment.foo
    e.g::
    
        environment.celery = "django"

    Used to make more environment variables available to your django project.
    Any value can be added after the "environment.". The example above adds::
    
        os.environ["celery"] = "django"

    to the django management scripts.

control-script
    The name of the main management script. Defaults to "django" so if your
    buildout:bin-directory = "bin" (as is the default), your management script
    will be located at "bin/django", and your wsgi script at "bin/django.wsgi".

eggs
    The eggs that you'd like to make available to your django project.


Bugs
====

This project is actively maintained, and bugs can be reported to
https://github.com/isotoma/isotoma.recipe.django/issues

Example with isotoma.recipe.apache
==================================

This example shows how isotoma.recipe.django and isotoma.recipe.apache can be
combined to create the wsgi script and an apache configuration that can run
that script. The generated apache config simply needs to be symlinked into
/etc/apache2/sites-available and you're away.

::

    [buildout]
    parts =
        django
        apache
    versions = versions
    eggs =
        foo
        django-treebeard

    [django]
    recipe = isotoma.recipe.django
    project = foo
    settings = production
    wsgi = true
    eggs = ${buildout:eggs}

    [eggpaths]
    recipe = isotoma.recipe.eggpaths

    [apache]
    recipe = isotoma.recipe.apache:wsgi
    interface = *
    sitename = example.com
    serveradmin = webmaster@example.com
    daemon = True
    user = ${django:project}
    group = ${:user}
    processgroup = ${:user}
    processes = 5
    threads = 10
    wsgi = django.wsgi
    static_aliases = /admin/media:${eggpaths:Django}django/contrib/admin/media
                     /media:${eggpaths:foo}/media

    [versions]
    Django = 1.3.1
