from django.conf.urls import url
from django.contrib import admin

from ip16dash.api.cmd.views import (
    JenkinsExec,
    JenkinsGetCmdLst,
)

urlpatterns = [
    url(r'^jen/(?P<cmd>[\w]+)/(?P<buildid>[\d]+)', JenkinsExec.as_view(),      name='jencmd'),
    url(r'^jenlst',                                JenkinsGetCmdLst.as_view(), name='jenlst')
]