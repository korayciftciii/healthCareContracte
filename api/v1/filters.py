import django_filters

from institutions.models import HealthInstitution, InstitutionContract


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class HealthInstitutionFilter(django_filters.FilterSet):
    """
    Kurumları doğrudan kurum özelliklerine göre filtreler.
    Şirket/ürün/network bazlı filtreleme için /contracts/ endpoint'ini kullanın.
    """
    city__plate_code = django_filters.NumberFilter(
        field_name="city__plate_code", lookup_expr="exact",
    )
    district = django_filters.NumberFilter(
        field_name="district", lookup_expr="exact",
    )
    institution_type__code = django_filters.CharFilter(
        field_name="institution_type__code", lookup_expr="exact",
    )

    class Meta:
        model = HealthInstitution
        fields = []


class InstitutionContractFilter(django_filters.FilterSet):
    """
    Anlaşmalı kurum sorgulama — şirket/ürün/network/poliçe uygulaması bazlı.
    Frontend bu endpoint'i kullanmalı.
    """
    company__code = django_filters.CharFilter(
        field_name="company__code", lookup_expr="exact",
    )
    product_type__code = django_filters.CharFilter(
        field_name="product_type__code", lookup_expr="exact",
    )
    city__plate_code = django_filters.NumberFilter(
        field_name="institution__city__plate_code", lookup_expr="exact",
    )
    district = django_filters.NumberFilter(
        field_name="institution__district", lookup_expr="exact",
    )
    institution_type__code = django_filters.CharFilter(
        field_name="institution__institution_type__code", lookup_expr="exact",
    )
    # Virgülle ayrılmış network id'leri: ?networks=1,2,3
    networks = NumberInFilter(
        field_name="networks", lookup_expr="in",
    )
    # Poliçe uygulaması bazlı filtre
    policy_application = django_filters.NumberFilter(
        field_name="policy_applications", lookup_expr="exact",
    )
    policy_application__service_id = django_filters.CharFilter(
        field_name="policy_applications__external_service_id", lookup_expr="exact",
    )

    class Meta:
        model = InstitutionContract
        fields = []
