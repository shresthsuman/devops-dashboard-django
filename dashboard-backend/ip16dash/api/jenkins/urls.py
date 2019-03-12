from django.conf.urls import url, include
from django.contrib import admin

from ip16dash.api.jenkins.views import (
    MainView,
    PipelinesView,
    JenkinsReleasesView,
    JenkinsReleasesMultiView,
    End2EndView,
    MultiList,
    MultiDetail,
)

urlpatterns = [
    url(r'^main/$'                      ,MainView.as_view(),name='main'),
    url(r'^(?P<name>[\w-]+)/pipelines/$',PipelinesView.as_view(),      name='pipelines'),
    url(r'^(?P<name>[\w-]+)/(?P<bname>[\w-]+)/sequences/$',JenkinsReleasesMultiView.as_view(),name='releasesmulti'),
    url(r'^(?P<name>[\w-]+)/sequences/$',JenkinsReleasesView.as_view(),name='releases'),
    url(r'^end2end/(?P<id>\d+)/$'       ,End2EndView.as_view(),        name='end2end'),
    url(r'^multi/list/$'                ,MultiList.as_view()  ,        name='multilst'),
    url(r'^multi/detail/(?P<name>[\w_]+)/$',MultiDetail.as_view(),     name='multidet'),
]
