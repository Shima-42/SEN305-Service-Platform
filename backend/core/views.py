from django.shortcuts import render

def home(request):
    context = {
        "platform_name" : "VUA ServiceDesk",
        "headline": "Report and track maintenance requests",
        "active_requests": 0,
    }
    return render(request, "core/home.html", context)

def about(request):
    project_roles = [
        "Requester",
        "Coordinator",
        "Technician",
        "Administrator",
    ]
    return render(request, "core/about.html", {"project_roles": project_roles})