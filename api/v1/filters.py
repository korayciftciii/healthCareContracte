import django_filters

from institutions.models import HealthInstitution


class NetworkInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class HealthInstitutionFilter(django_filters.FilterSet):
    networks = NetworkInFilter(field_name="networks", lookup_expr="in")

    class Meta:
        model = HealthInstitution
        fields = {
            "company__code": ["exact"],
            "city__plate_code": ["exact"],
            "district": ["exact"],
            "product_type__code": ["exact"],
            "institution_type__code": ["exact"],
        }
