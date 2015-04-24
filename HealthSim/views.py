import json
import socket

from django.shortcuts import render

from django.http import HttpResponse, Http404
from django.views.generic import TemplateView

from .insurance import plans as plans

plans.load_plans()

class HealthSimView(TemplateView):
    template_name = "First.html"
    #template_name = "health_sim_template.html"

def ajax_view_0(request):

    if 'client_ajax_input_0' in request.POST:
        response_dict = {}
        response_dict.update({'response_item_0': "I am item 0 :)", 'response_item_1' : "I am item 1 and I'm a loser :("})
        return HttpResponse(json.dumps(response_dict), content_type='application/json')
    else:
        raise Http404("IDK LOL")

def get_service_list_view(request):
    if 'client_ajax_input_0' in request.POST:
        response_dict = {} 
        # Populate with Nate's method, for now use this
        response_dict = {"service_list" : [{
            "name" : name, "service" : service } 
            for name, service in plans.get_service_list()]}
        #response_dict.update({"service_list" : [{"name": "Primary Care Physician", "service": "pcp"}, {"name": "Emergency Room", "service": "er"}]});
        return HttpResponse(json.dumps(response_dict), content_type='application/json')
    else:
        raise Http404("IDK")

