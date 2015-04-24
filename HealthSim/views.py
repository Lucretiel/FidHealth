import json
import socket

from django.shortcuts import render

from django.http import HttpResponse, Http404
from django.views.generic import TemplateView


#def health_sim_home(request):
#    return HttpResponse("Hello, No0bs! Welcome to HealthSim.")

class HealthSimView(TemplateView):
    template_name = "health_sim_template.html"

def ajax_view_0(request):

    if 'client_ajax_input_0' in request.POST:
        response_dict = {}
        response_dict.update({'response_item_0': "I am item 0 :)", 'response_item_1' : "I am item 1 and I'm a loser :("})
        return HttpResponse(json.dumps(response_dict), content_type='application/json')
    else:
        return Http404("IDK LOL")
