from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from companies.models import InsuranceCompany
from geo.models import City, District
from institutions.models import HealthInstitution
from products.models import InstitutionType, ProductType

from .serializers import (
    CitySerializer,
    DistrictSerializer,
    HealthInstitutionSerializer,
    InstitutionTypeSerializer,
    InsuranceCompanySerializer,
    ProductTypeSerializer,
)


class InsuranceCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InsuranceCompany.objects.filter(is_active=True)
    serializer_class = InsuranceCompanySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]
    pagination_class = None


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    pagination_class = None


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.select_related("city").all()
    serializer_class = DistrictSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["city"]
    search_fields = ["name"]
    pagination_class = None


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer
    pagination_class = None


class InstitutionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InstitutionType.objects.all()
    serializer_class = InstitutionTypeSerializer
    pagination_class = None


class HealthInstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthInstitution.objects.select_related(
        "company", "product_type", "institution_type", "city", "district"
    ).filter(is_active=True)
    serializer_class = HealthInstitutionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        "company__code": ["exact"],
        "city__plate_code": ["exact"],
        "district": ["exact"],
        "product_type__code": ["exact"],
        "institution_type__code": ["exact"],
    }
    search_fields = ["name", "address"]
