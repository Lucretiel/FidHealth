from django.conf.urls import patterns, url, include

from HealthSim.views import HealthSimView
from HealthSim.views import ajax_view_0
from HealthSim.views import get_service_list_view

urlpatterns = patterns('',
        url(r'^get_service_list$', get_service_list_view), 
        url(r'^ajax_json_0$', ajax_view_0), 
        url(r'^$', HealthSimView.as_view()), 
)
