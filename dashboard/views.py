from django.shortcuts import render
from dashboard.models import Sector, Bivalvo

def home(request):
    bivalvos = Bivalvo.objects.all()
    sectores = Sector.objects.all()
    context = {
        'bivalvos': bivalvos,
        'sectores': sectores,
    }
    print("Bivalvos:", bivalvos)
    
    return render(request, 'dashboard/home.html', context)

def sector_detail(request, id):
    sector = Sector.objects.get(id=id)
    context = {
        'sector': sector,
    }
    return render(request, 'dashboard/sector_detail.html', context)
    
