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
        print("Checking..")
        if 'client_ajax_input_0' in request.POST:
            print("Have dummY")
        else:
            print("no dummy")
        if 'client_input_dict' in request.POST:
            print("Hurray!")
        else:
            print("No data :(")
        tempList = request.POST.getlist('client_input_dict')
        print("array:")
        print(tempList[0])

        # Get inputs
        try:
            response_list = [] 
            response_list = request.POST.getlist('client_input_dict')
            simulation_input = {"me" : json.loads(response_list[0])}
            # Run simulation if we have input
            simulation_result = {}
            if simulation_input:
                print("Simulation input:",simulation_input)
                simulation_result = run_simulations(simulation_input)
        except Exception:
            print('\n'.join(traceback.format_exception(*sys.exc_info())))
            raise

        # Send results 
        response_dict = {}
        for entry in simulation_result:
            response_dict.update(entry)
        #response_dict.update({'response_item_0': "I am item 0 :)", 'response_item_1' : "I am item 1 and I'm a loser :("})
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

