from django.conf.urls import url
from django.contrib import admin

from ip16dash.api.env.views import (
    IPCreate,
    IPDelete,
    IPList,
)

urlpatterns = [
    url(r'^create'               ,IPCreate.as_view(), name='ipcreate'),
    url(r'^delete/(?P<pk>[\d]+)$',IPDelete.as_view(), name='ipdelete'),
    url(r'^list'                 ,IPList.as_view(),   name='iplist'),
]