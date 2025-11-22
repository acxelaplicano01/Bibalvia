from rest_framework import serializers

class LecturaSerializer(serializers.Serializer):
    sector_id = serializers.IntegerField()
    temperatura = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    salinidad = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)
    ph = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)
    turbidez = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    humedad = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    marca_tiempo = serializers.DateTimeField()