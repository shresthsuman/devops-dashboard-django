from django.conf.urls import url
from django.contrib import admin

from ip16dash.api.proj.views import (
    ProjectsList,
    ProjectsCreate,
    ProjectsDelete,
    ProjectsUpdate,
)

urlpatterns = [
    url(r'^create'               ,ProjectsCreate.as_view(), name='ipcreate'),
    url(r'^delete/(?P<pk>[\d]+)$',ProjectsDelete.as_view(), name='ipdelete'),
    url(r'^list'                 ,ProjectsList.as_view(),   name='iplist'),
    url(r'^update/(?P<pk>[\d]+)$',ProjectsUpdate.as_view(), name='update'),
]