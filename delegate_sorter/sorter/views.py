from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
from .services import get_all_rows


def index(request):
    return HttpResponse("Welcome to the delegate sorter")

def info(request):
    info = get_all_rows("Test Sheets")
    return render(request, 'display_info.html', {'info': info})