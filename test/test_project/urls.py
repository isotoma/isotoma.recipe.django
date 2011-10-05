from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.views.generic.simple import direct_to_template
from django.conf import settings

urlpatterns = patterns('',
    url('^$', direct_to_template, {'template': 'placeholder.html'}),
)

# Serve media when in DEBUG mode.
if settings.DEBUG:
    urlpatterns += patterns('',
        url(
            r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:], 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            'show_indexes': True
            }
        ),
    )
