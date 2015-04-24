from django.conf.urls import patterns, url, include

from HealthSim.views import HealthSimView
from HealthSim.views import ajax_view_0

urlpatterns = patterns('',
        url(r'^$', HealthSimView.as_view()), 
        #url(r'^ajax_json_0$', HealthSim.views.ajax_view_0), 
        url(r'^ajax_json_0$', ajax_view_0), 
)
