from django.http import HttpResponse
from django.shortcuts import render

def home_page(request):
    # return HttpResponse("Hello world! This is the home page.")
    return render(request, 'home.html')