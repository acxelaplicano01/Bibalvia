from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from decimal import Decimal
import random
from dashboard.models import (
    Sector, 
    Bivalvo, 
    HistorialTemperatura, 
    HistorialSalinidad,
    HistorialPh,
    HistorialHumedad,
    HistorialTurbidez,
    HistorialClasificacion
)

class Command(BaseCommand):
    help = 'Seed database with initial data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            
            # Eliminar datos
            HistorialClasificacion.objects.all().delete()
            HistorialTemperatura.objects.all().delete()
            HistorialSalinidad.objects.all().delete()
            HistorialHumedad.objects.all().delete()
            HistorialPh.objects.all().delete()
            HistorialTurbidez.objects.all().delete()
            Bivalvo.objects.all().delete()
            Sector.objects.all().delete()
            
            # Resetear secuencias de autoincremento
            with connection.cursor() as cursor:
                tablas = [
                    'dashboard_sector',
                    'dashboard_bivalvo',
                    'dashboard_historialtemperatura',
                    'dashboard_historialsalinidad',
                    'dashboard_historialph',
                    'dashboard_historialhumedad',
                    'dashboard_historialturbidez',
                    'dashboard_historialclasificacion'
                ]
                for tabla in tablas:
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{tabla}'")
            
            self.stdout.write(self.style.SUCCESS('Data cleared and IDs reset!'))

        self.stdout.write('Seeding database...')

        # Crear sectores
        sectores = [
            Sector.objects.create(latitud=Decimal('14.0583'), longitud=Decimal('-87.2068')),
            Sector.objects.create(latitud=Decimal('15.5000'), longitud=Decimal('-88.0250')),
            Sector.objects.create(latitud=Decimal('13.4894'), longitud=Decimal('-86.5780')),
        ]
        self.stdout.write(self.style.SUCCESS(f'Created {len(sectores)} sectors'))

        # Crear bivalvos
        bivalvos = [
            Bivalvo.objects.create(tipo='Ostra'),
            Bivalvo.objects.create(tipo='Almeja'),
            Bivalvo.objects.create(tipo='Mejillón'),
        ]
        self.stdout.write(self.style.SUCCESS(f'Created {len(bivalvos)} bivalves'))

        # Crear historial de temperatura
        count = 0
        for sector in sectores:
            for i in range(30):  # 30 registros por sector
                HistorialTemperatura.objects.create(
                    sector=sector,
                    valor=Decimal(str(round(random.uniform(20.0, 32.0), 2))),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} temperature records'))

        # Crear historial de salinidad
        count = 0
        for sector in sectores:
            for i in range(30):
                HistorialSalinidad.objects.create(
                    sector=sector,
                    valor=Decimal(str(round(random.uniform(30.0, 38.0), 2))),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} salinity records'))
        
        # Crear historial de pH
        count = 0
        for sector in sectores:
            for i in range(30):
                HistorialPh.objects.create(
                    sector=sector,
                    valor=Decimal(str(round(random.uniform(6.5, 8.5), 2))),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} pH records'))

        # Crear historial de humedad
        count = 0
        for sector in sectores:
            for i in range(30):
                HistorialHumedad.objects.create(
                    sector=sector,
                    valor=Decimal(str(round(random.uniform(60.0, 95.0), 2))),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} humidity records'))

        # Crear historial de turbidez
        count = 0
        for sector in sectores:
            for i in range(30):
                HistorialTurbidez.objects.create(
                    sector=sector,
                    valor=Decimal(str(round(random.uniform(0.5, 50.0), 2))),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i)
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} turbidity records'))

        # Crear historial de clasificación
        count = 0
        for sector in sectores:
            for i in range(10):
                HistorialClasificacion.objects.create(
                    sector=sector,
                    bivalvo=random.choice(bivalvos),
                    marca_tiempo=timezone.now() - timezone.timedelta(days=i, hours=random.randint(0, 23))
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} classification records'))

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))