from django.db import models

class Bivalvo(models.Model):
    tipo = models.CharField(max_length=100)

class Sector(models.Model):
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)

class Historial_Clasificacion(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    bivalvo_id = models.ForeignKey(Bivalvo, on_delete=models.CASCADE)
    marca_tiempo = models.DateTimeField()


class Historial_Humedad(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=5, decimal_places=2)
    marca_tiempo = models.DateTimeField()

class Historial_Temperatura(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=5, decimal_places=2)
    marca_tiempo = models.DateTimeField()

class Historial_Turbidez(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=6, decimal_places=2)
    marca_tiempo = models.DateTimeField()

class Historial_Ph(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=4, decimal_places=2)
    marca_tiempo = models.DateTimeField()

class Historial_Salinidad(models.Model):
    sector_id = models.ForeignKey(Sector, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=4, decimal_places=2)
    marca_tiempo = models.DateTimeField()