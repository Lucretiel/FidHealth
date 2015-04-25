from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^HealthSim/', include('HealthSim.urls')),
]

# Run this code once on Django startup.
#TODO
