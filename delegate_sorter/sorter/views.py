from django.shortcuts import render

# Create your views here.
    
from .services import get_all_records
from django.shortcuts import render

def info(request):
    #Gets all the information for the GSheet named "Test sheet"
    info = get_all_records("Test sheet")
    return render(request, 'display_info.html', {'info': info})

