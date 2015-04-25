import traceback
import sys
import json
import socket

from django.shortcuts import render

from django.http import HttpResponse, Http404
from django.views.generic import TemplateView

from .insurance import plans as plans
from .insurance.plans import run_simulations

plans.load_plans()

class HealthSimView(TemplateView):
    template_name = "First.html"
    #template_name = "health_sim_template.html"

def ajax_view_0(request):

    if request.method == "POST":
        # Get inputs
        response_list = [] 
        response_list = request.POST.getlist('client_input_dict')
        simulation_input = {"me" : json.loads(response_list[0])}
        # Run simulation if we have input
        simulation_result = {}
        if simulation_input:
            simulation_result = run_simulations(simulation_input)

        return HttpResponse(json.dumps(simulation_result), content_type='application/json')
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

