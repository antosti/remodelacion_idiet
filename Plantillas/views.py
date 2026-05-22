from django.shortcuts import render

# Create your views here.
def list_templates(request):
    return render(request, 'admin/list_templates.html')