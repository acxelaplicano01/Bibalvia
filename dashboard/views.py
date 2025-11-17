from django.shortcuts import render, redirect
from dashboard.models import Sector, Bivalvo, Zona
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

def home(request):
    sectores = Sector.objects.all()
    context = {
        'sectores': sectores,
    }
    
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
        tipo = request.POST.get('tipo')
        
        if tipo == 'zona':
            # Guardar nueva zona
            nombre = request.POST.get('nombre')
            coordenadas = request.POST.get('coordenadas')
            
            if nombre and coordenadas:
                try:
                    coords_json = json.loads(coordenadas)
                    # Convertir a formato GeoJSON
                    geojson = {
                        "type": "Polygon",
                        "coordinates": [[
                            [coord['lng'], coord['lat']] for coord in coords_json
                        ] + [[coords_json[0]['lng'], coords_json[0]['lat']]]]  # Cerrar el polígono
                    }
                    
                    zona = Zona.objects.create(
                        nombre=nombre,
                        geopoligono=geojson
                    )
                    return JsonResponse({
                        'success': True,
                        'mensaje': f'Zona "{nombre}" creada exitosamente',
                        'zona': {
                            'id': zona.id,
                            'nombre': zona.nombre,
                            'geopoligono': zona.geopoligono
                        }
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'mensaje': f'Error al crear zona: {str(e)}'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'Faltan datos para crear la zona'
                }, status=400)
        
        elif tipo == 'punto':
            # Guardar nuevo sector
            latitud = request.POST.get('latitud')
            longitud = request.POST.get('longitud')
            nombre_sector = request.POST.get('nombre_sector')
            zonas_ids = request.POST.get('zonas_ids', '')
            
            if latitud and longitud:
                try:
                    sector = Sector.objects.create(
                        latitud=float(latitud),
                        longitud=float(longitud),
                        nombre_sector=nombre_sector if nombre_sector else None
                    )
                    
                    # Asociar zonas si existen
                    if zonas_ids:
                        zona_ids_list = [int(id) for id in zonas_ids.split(',') if id]
                        sector.zonas.set(zona_ids_list)
                    
                    return redirect(f'/?toast=Sector creado exitosamente en ({latitud}, {longitud})&toast_tipo=success')
                except ValueError:
                    return redirect('/?toast=Coordenadas inválidas&toast_tipo=error')
            else:
                return redirect('/?toast=Por favor selecciona una ubicación en el mapa&toast_tipo=error')
    
    # GET: Cargar todas las zonas
    zonas = Zona.objects.all()
    context = {
        'zonas': list(zonas.values('id', 'nombre', 'geopoligono'))
    }
    return render(request, 'dashboard/sector_create.html', context)