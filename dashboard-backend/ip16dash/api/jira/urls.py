from django.conf.urls import url, include
from django.contrib import admin

from ip16dash.api.jira.views import (
    JiraCollectorList,
    JiraCollectorIssue,
    JiraAggregations,
    JiraAggregationsList,
)

urlpatterns = [
    url(r'^list/$'                       ,JiraCollectorList.as_view()   ,name='jiralist'),
    url(r'^getkey/(?P<issue>[\w]+-[\w]+)',JiraCollectorIssue.as_view()  ,name='jiraissue'),
    url(r'^aggr/(?P<issue>[\w]+-[\w]+)'  ,JiraAggregations.as_view()    ,name='jiraaggr'),
    url(r'^aggr/list/$'                  ,JiraAggregationsList.as_view(),name='jiraaggrlist'),
]
