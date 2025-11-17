from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Sector(models.Model):
    latitud = models.DecimalField(
        max_digits=10, 
        decimal_places=8,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitud = models.DecimalField(
        max_digits=11, 
        decimal_places=8,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    
    nombre_sector= models.CharField(max_length=100, unique=True, null=True, blank=True)
    

    zonas = models.ManyToManyField('Zona', related_name='sectores')
    
    class Meta:
        verbose_name = "Sector"
        verbose_name_plural = "Sectores"
        ordering = ['id']
        indexes = [
            models.Index(fields=['latitud', 'longitud']),
        ]
    
    def __str__(self):
        return f"Sector {self.id} ({self.latitud}, {self.longitud})"


class Bivalvo(models.Model):
    tipo = models.CharField(max_length=100, db_index=True)
    
    class Meta:
        verbose_name = "Bivalvo"
        verbose_name_plural = "Bivalvos"
        ordering = ['tipo']
    
    def __str__(self):
        return self.tipo


class HistorialTemperatura(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='temperaturas'  # ← IMPORTANTE
    )
    valor = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(-50), MaxValueValidator(100)]
    )
    marca_tiempo = models.DateTimeField(db_index=True)  # ← Para búsquedas por fecha
    
    class Meta:
        verbose_name = "Historial de Temperatura"
        verbose_name_plural = "Historiales de Temperatura"
        ordering = ['-marca_tiempo']  # Más recientes primero
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
        ]
    
    def __str__(self):
        return f"{self.valor}°C - {self.marca_tiempo}"


class HistorialSalinidad(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='salinidades'
    )
    valor = models.DecimalField(max_digits=4, decimal_places=2)
    marca_tiempo = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Historial de Salinidad"
        verbose_name_plural = "Historiales de Salinidad"
        ordering = ['-marca_tiempo']
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
        ]
    
    def __str__(self):
        return f"{self.valor} PSU - {self.marca_tiempo}"


class HistorialPh(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='ph_registros'
    )
    valor = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(14)]
    )
    marca_tiempo = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Historial de pH"
        verbose_name_plural = "Historiales de pH"
        ordering = ['-marca_tiempo']
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
        ]
    
    def __str__(self):
        return f"pH {self.valor} - {self.marca_tiempo}"


class HistorialTurbidez(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='turbideces'
    )
    valor = models.DecimalField(max_digits=6, decimal_places=2)
    marca_tiempo = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Historial de Turbidez"
        verbose_name_plural = "Historiales de Turbidez"
        ordering = ['-marca_tiempo']
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
        ]
    
    def __str__(self):
        return f"{self.valor} NTU - {self.marca_tiempo}"


class HistorialHumedad(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='humedades'
    )
    valor = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    marca_tiempo = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Historial de Humedad"
        verbose_name_plural = "Historiales de Humedad"
        ordering = ['-marca_tiempo']
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
        ]
    
    def __str__(self):
        return f"{self.valor}% - {self.marca_tiempo}"


class HistorialClasificacion(models.Model):
    sector = models.ForeignKey(
        Sector, 
        on_delete=models.CASCADE,
        related_name='clasificaciones'
    )
    bivalvo = models.ForeignKey(
        Bivalvo, 
        on_delete=models.CASCADE,
        related_name='clasificaciones'
    )
    marca_tiempo = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Historial de Clasificación"
        verbose_name_plural = "Historiales de Clasificación"
        ordering = ['-marca_tiempo']
        indexes = [
            models.Index(fields=['sector', '-marca_tiempo']),
            models.Index(fields=['bivalvo', '-marca_tiempo']),
        ]
        # Evitar duplicados
        constraints = [
            models.UniqueConstraint(
                fields=['sector', 'bivalvo', 'marca_tiempo'],
                name='unique_clasificacion'
            )
        ]
    
    def __str__(self):
        return f"{self.bivalvo.tipo} en {self.sector} - {self.marca_tiempo}"

class Zona(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    geopoligono = models.JSONField()  # GeoJSON del polígono

    def __str__(self):
        return self.nombre
