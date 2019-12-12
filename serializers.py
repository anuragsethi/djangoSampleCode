"""
    Serializer classes
    Grass potential serializer, Date & pouches, Lawn engine serializer.
    Classes to handle the serialization and deserialization of objects.
"""
from rest_framework import serializers
from ..models import DateAndPouches, LawnEngine, GrassPotential, InternalParameters


class GrassPotentialSerializer(serializers.ModelSerializer):
    """Grass potential for lawn engine serializer

    """
    class Meta:
        """Meta class attributes
        # handles only these fields.
        """
        model = GrassPotential
        fields = ("date", "value")


class DateAndPouchesSerializer(serializers.ModelSerializer):
    """Date and pouches for lawn engine serializer

    """
    class Meta:
        """Meta class attributes
        # handles only these fields.
        """
        model = DateAndPouches
        fields = ("date", "pouches")


class LawnEngineSerializer(serializers.ModelSerializer):
    """
        Lawn engine serializer
    """
    grass_potential = GrassPotentialSerializer(many=True)
    date_and_pouches = DateAndPouchesSerializer(many=True)

    class Meta:
        """Meta class attributes

        """
        model = LawnEngine
        # handles all fields.
        fields = '__all__'


class InternalParameterSerializer(serializers.ModelSerializer):
    """
        Internal lawn parameter serializer for saving fetch and updating data.
    """
    class Meta:
        """Meta class attributes

        """
        model = InternalParameters
        # handles only these fields.
        fields = (
            'id',
            'parameter_name',
            'production_value',
            'default_value',
            'updated_at'
        )
