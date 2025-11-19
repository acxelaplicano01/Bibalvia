from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import Bivalvo

class Command(BaseCommand):
    help = 'Seed Bivalvos + Admin User'

    def handle(self, *args, **options):
        # Bivalvos
        tipos = ['Ostra', 'Almeja', 'Mejillón']
        existentes = Bivalvo.objects.values_list('tipo', flat=True)

        for tipo in tipos:
            if tipo not in existentes:
                Bivalvo.objects.create(tipo=tipo)

        self.stdout.write(self.style.SUCCESS('Bivalvos creados'))

        # Admin
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                password="admin321",
                email="admin@example.com"
            )
            self.stdout.write(self.style.SUCCESS('Admin creado'))
        else:
            self.stdout.write('Admin ya existe')

        self.stdout.write(self.style.SUCCESS('Seeder listo 🚀'))
