
# mostly taken from here: http://blog.dscpl.com.au/2010/03/improved-wsgi-script-for-use-with.html

def main(settings):
    
    import django.core.management
    django.core.management.setup_environ(settings)
    utility = django.core.management.ManagementUtility()
    command = utility.fetch_command('runserver')
    
    command.validate()
    
    import django.conf
    import django.utils
    
    django.utils.translation.activate(django.conf.settings.LANGUAGE_CODE)
    
    import django.core.handlers.wsgi
    
    return django.core.handlers.wsgi.WSGIHandler()