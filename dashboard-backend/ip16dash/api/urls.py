from django.conf.urls import url, include
from django.contrib import admin

urlpatterns = [
    url(r'^auth/',   include("ip16dash.api.auth.urls",    namespace='auth')),
    url(r'^cmd/',    include("ip16dash.api.cmd.urls",     namespace='cmd')),
    url(r'^env/',    include("ip16dash.api.env.urls",     namespace='env')),
    url(r'^proj/',   include("ip16dash.api.proj.urls",    namespace='proj')),
    url(r'^remote/', include("ip16dash.api.remote.urls",  namespace='remote')),
    url(r'^jenkins/',include("ip16dash.api.jenkins.urls", namespace='jenkins')),
    url(r'^jira/',   include("ip16dash.api.jira.urls",    namespace='jira')),
]
