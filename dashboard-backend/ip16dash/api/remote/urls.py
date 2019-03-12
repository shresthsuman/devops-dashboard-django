from django.conf.urls import url
from django.contrib import admin

from ip16dash.api.remote.views import (
    RemoteCollectorCreate,
    RemoteCollectorDetail,
    RemoteCollectorDelete,
    RemoteCollectorList,
    RemoteCollectorUpdate,
    RemoteCollectorRun,
)

urlpatterns = [
    url(r'^list/$'             ,RemoteCollectorList.as_view()  ,name='remotelist'),
    url(r'^detail/(?P<pk>\d+)$',RemoteCollectorDetail.as_view(),name='remotedetail'),
    url(r'^create/$'           ,RemoteCollectorCreate.as_view(),name='remotecreate'),
    url(r'^update/(?P<pk>\d+)$',RemoteCollectorUpdate.as_view(),name='remoteupdate'),
    url(r'^delete/(?P<pk>\d+)$',RemoteCollectorDelete.as_view(),name='remotedelete'),
    url(r'^run/(?P<pk>\d+)$'   ,RemoteCollectorRun.as_view()   ,name='remoterun'),
]
