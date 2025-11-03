from django.shortcuts import render, redirect
from dashboard.models import Sector, Bivalvo
from django.contrib import messages

def home(request):
    sectores = Sector.objects.all()
    context = {
        'sectores': sectores,
    }
    
    # Capturar parámetros de toast desde la URL
    toast = request.GET.get('toast')
    toast_tipo = request.GET.get('toast_tipo', 'success')
    
    if toast:
        context['toast'] = toast
        context['toast_tipo'] = toast_tipo
        
    
    return render(request, 'dashboard/home.html', context)

def sector_detail(request, id):
    sector = Sector.objects.get(id=id)
    context = {
        'sector': sector,
    }
    return render(request, 'dashboard/sector_detail.html', context)

def sector_create(request):
    if request.method == 'POST':
        latitud = request.POST.get('latitud')
        longitud = request.POST.get('longitud')
        
        if latitud and longitud:
            try:
                Sector.objects.create(
                    latitud=float(latitud),
                    longitud=float(longitud)
                )
                # Redirigir a una vista que setea el mensaje en JavaScript
                return redirect(f'/?toast=Sector creado exitosamente en ({latitud}, {longitud})&toast_tipo=success')
            except ValueError:
                return redirect('/?toast=Coordenadas inválidas&toast_tipo=error')
        else:
            return redirect('/?toast=Por favor selecciona una ubicación en el mapa&toast_tipo=error')
    
    return render(request, 'dashboard/sector_create.html')
    
