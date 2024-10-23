from django.shortcuts import render

# Create your views here.
    
from .services import get_all_rows
from django.shortcuts import render

def info(request):
    info = get_all_rows("Test sheet")
    return render(request, 'display_info.html', {'info': info})