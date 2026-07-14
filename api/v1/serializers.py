from rest_framework import serializers

from companies.models import InsuranceCompany, Network
from geo.models import City, District
from institutions.models import HealthInstitution
from products.models import InstitutionType, ProductType


class InsuranceCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceCompany
        fields = ["id", "name", "code", "slug", "is_active"]


class NetworkSerializer(serializers.ModelSerializer):
    company = serializers.SlugRelatedField(slug_field="code", read_only=True)
    product_type = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Network
        fields = ["id", "name", "company", "product_type", "shown_by_default"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "plate_code"]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name", "city"]


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ["id", "name", "code"]


class InstitutionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionType
        fields = ["id", "name", "code"]


class HealthInstitutionSerializer(serializers.ModelSerializer):
    company = serializers.SlugRelatedField(slug_field="code", read_only=True)
    product_type = serializers.SlugRelatedField(slug_field="code", read_only=True)
    institution_type = serializers.SlugRelatedField(
        slug_field="code", read_only=True, allow_null=True
    )
    city = serializers.SlugRelatedField(slug_field="name", read_only=True, allow_null=True)
    district = serializers.SlugRelatedField(slug_field="name", read_only=True, allow_null=True)
    networks = NetworkSerializer(many=True, read_only=True)

    class Meta:
        model = HealthInstitution
        fields = [
            "id",
            "external_id",
            "name",
            "address",
            "phone",
            "latitude",
            "longitude",
            "company",
            "product_type",
            "institution_type",
            "city",
            "district",
            "networks",
            "is_active",
            "last_seen_at",
        ]
