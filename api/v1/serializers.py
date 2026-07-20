from rest_framework import serializers

from companies.models import InsuranceCompany, Network, PolicyApplication
from geo.models import City, District
from institutions.models import HealthInstitution, InstitutionContract
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


class PolicyApplicationSerializer(serializers.ModelSerializer):
    company = serializers.SlugRelatedField(slug_field="code", read_only=True)
    product_type = serializers.SlugRelatedField(slug_field="code", read_only=True)
    network = NetworkSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PolicyApplication
        fields = [
            "id", "name", "code", "external_service_id",
            "company", "product_type", "network", "is_active",
        ]


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
    """Şirketten bağımsız saf kurum bilgisi."""
    institution_type = serializers.SlugRelatedField(
        slug_field="code", read_only=True, allow_null=True,
    )
    city = serializers.SlugRelatedField(slug_field="name", read_only=True, allow_null=True)
    district = serializers.SlugRelatedField(slug_field="name", read_only=True, allow_null=True)

    class Meta:
        model = HealthInstitution
        fields = [
            "id", "name", "slug",
            "address", "phone", "latitude", "longitude",
            "institution_type", "city", "district",
            "is_active",
        ]


class InstitutionContractSerializer(serializers.ModelSerializer):
    """Kurum anlaşması — şirket + ürün + network + poliçe uygulamaları."""
    institution = HealthInstitutionSerializer(read_only=True)
    company = serializers.SlugRelatedField(slug_field="code", read_only=True)
    product_type = serializers.SlugRelatedField(slug_field="code", read_only=True)
    networks = NetworkSerializer(many=True, read_only=True)
    policy_applications = PolicyApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = InstitutionContract
        fields = [
            "id",
            "institution",
            "company", "product_type",
            "external_id",
            "networks",
            "policy_applications",
            "coverage_notes",
            "is_active",
            "last_seen_at",
        ]
