from django.conf.urls import url, include
from django.contrib import admin

from ip16dash import views

app_name = 'ip16dash'

urlpatterns = [
	url(r'^api/', include("ip16dash.api.urls", namespace='api')),
]
