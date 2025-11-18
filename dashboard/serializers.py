from rest_framework import serializers

class LecturaSerializer(serializers.Serializer):
    sector_id = serializers.IntegerField()
    temperatura = serializers.DecimalField(max_digits=5, decimal_places=2)
    salinidad = serializers.DecimalField(max_digits=4, decimal_places=2)
    ph = serializers.DecimalField(max_digits=4, decimal_places=2)
    turbidez = serializers.DecimalField(max_digits=6, decimal_places=2)
    humedad = serializers.DecimalField(max_digits=5, decimal_places=2)
    marca_tiempo = serializers.DateTimeField()