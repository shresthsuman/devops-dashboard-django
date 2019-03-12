from django.conf.urls import url, include
from django.contrib import admin

from ip16dash.api.auth.views import (
    UserCreate,
    UserLogin,
    UserDelete,
    UserList,
    UserUpdate,
)

from django.views.decorators.csrf import csrf_exempt
from rest_framework_jwt.views import refresh_jwt_token
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
    url(r'^token/$'                        ,obtain_jwt_token),
    url(r'^refresh/$'                      ,refresh_jwt_token),

    url(r'^create/$'                       ,UserCreate.as_view(),name='create'),
    url(r'^list/$'                         ,UserList.as_view()  ,name='list'),
    url(r'^update/(?P<username>[\w]+)$'    ,UserUpdate.as_view(),name='update'),
    url(r'^delete/(?P<username>[\w]+)$'    ,UserDelete.as_view(),name='delete'),
    url(r'^login/$'                        ,UserLogin.as_view() ,name='login'),
]