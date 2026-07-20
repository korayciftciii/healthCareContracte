from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from companies.models import InsuranceCompany, Network, PolicyApplication
from geo.models import Province, District
from institutions.models import HealthInstitution, InstitutionContract
from products.models import InstitutionType, ProductType

from .filters import HealthInstitutionFilter, InstitutionContractFilter
from .serializers import (
    ProvinceSerializer,
    DistrictSerializer,
    HealthInstitutionSerializer,
    InstitutionContractSerializer,
    InstitutionTypeSerializer,
    InsuranceCompanySerializer,
    NetworkSerializer,
    PolicyApplicationSerializer,
    ProductTypeSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="Sigorta şirketlerini listele",
        description="Sistemde tanımlı sigorta şirketlerini döner. Dropdown/filtre doldurmak için kullanılır.",
        tags=["Referans Veriler"],
    ),
    retrieve=extend_schema(summary="Tek bir sigorta şirketinin detayı", tags=["Referans Veriler"]),
)
class InsuranceCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InsuranceCompany.objects.filter(is_active=True)
    serializer_class = InsuranceCompanySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="İlleri listele",
        description="Türkiye'nin 81 ilini plaka koduyla birlikte döner.",
        tags=["Referans Veriler"],
    ),
    retrieve=extend_schema(summary="Tek bir ilin detayı", tags=["Referans Veriler"]),
)
class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="İlçeleri listele",
        description="`?province=<il id>` ile belirli bir ile ait ilçeleri filtreleyebilirsin.",
        tags=["Referans Veriler"],
        parameters=[
            OpenApiParameter(
                "province", int, description="İl id'sine göre filtrele (province/ ucundaki `id` alanı).",
            ),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir ilçenin detayı", tags=["Referans Veriler"]),
)
class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.select_related("province").filter(is_active=True)
    serializer_class = DistrictSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["province"]
    search_fields = ["name"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="Ürün tiplerini listele",
        description="TSS (Tamamlayıcı Sağlık Sigortası) ve ÖSS (Özel Sağlık Sigortası).",
        tags=["Referans Veriler"],
    ),
    retrieve=extend_schema(summary="Tek bir ürün tipinin detayı", tags=["Referans Veriler"]),
)
class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="Kurum tiplerini listele",
        description="Hastane, Tıp Merkezi, Diş Hekimi, Optik, Medikal vb.",
        tags=["Referans Veriler"],
    ),
    retrieve=extend_schema(summary="Tek bir kurum tipinin detayı", tags=["Referans Veriler"]),
)
class InstitutionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InstitutionType.objects.all()
    serializer_class = InstitutionTypeSerializer
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="Network / Plan gruplarını listele",
        description=(
            "Bir sigorta şirketinin bir ürün tipi içindeki plan grupları.\n\n"
            "TSS örnekleri: 'Sağlığım Tamam Sigortası', 'AXA Sağlığım Tamam Tutumlu'.\n"
            "ÖSS örnekleri: 'Network 1', 'Network 2', 'Network 3'.\n\n"
            "`?company__code=AXA&product_type__code=TSS` ile filtrelenir."
        ),
        tags=["Referans Veriler"],
        parameters=[
            OpenApiParameter("company__code", str, description="Şirket kodu."),
            OpenApiParameter("product_type__code", str, description="TSS veya OSS."),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir network'ün detayı", tags=["Referans Veriler"]),
)
class NetworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Network.objects.select_related("company", "product_type").all()
    serializer_class = NetworkSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        "company__code": ["exact"],
        "product_type__code": ["exact"],
    }
    search_fields = ["name"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="Poliçe uygulamalarını listele",
        description=(
            "Bir network altındaki poliçe uygulamaları. Her uygulama şirketin API'sindeki\n"
            "bir `external_service_id`'ye (örn. AXA ServiceId) karşılık gelir.\n\n"
            "Kurumları bu uygulamalar bazında sorgulamak için /contracts/ endpoint'ini kullanın."
        ),
        tags=["Referans Veriler"],
        parameters=[
            OpenApiParameter("company__code", str, description="Şirket kodu."),
            OpenApiParameter("product_type__code", str, description="TSS veya OSS."),
            OpenApiParameter("network", int, description="Network id'si."),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir poliçe uygulamasının detayı", tags=["Referans Veriler"]),
)
class PolicyApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PolicyApplication.objects.select_related(
        "company", "product_type", "network",
    ).filter(is_active=True)
    serializer_class = PolicyApplicationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        "company__code": ["exact"],
        "product_type__code": ["exact"],
        "network": ["exact"],
    }
    search_fields = ["name", "code", "external_service_id"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="Sağlık kurumlarını listele (saf kurum verileri)",
        description=(
            "Şirketten bağımsız saf kurum listesi. Adres, telefon, koordinat bilgilerini içerir.\n\n"
            "Bir şirket/network bazında anlaşmalı kurum sorgulamak için "
            "`/contracts/` endpoint'ini kullanın."
        ),
        tags=["Sağlık Kurumları"],
        parameters=[
            OpenApiParameter("province__plate_code", int, description="İl plaka kodu."),
            OpenApiParameter("district", int, description="İlçe id'si."),
            OpenApiParameter("institution_type__code", str, description="Kurum tipi kodu."),
            OpenApiParameter("search", str, description="Kurum adı/adresinde serbest metin arama."),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir sağlık kurumunun detayı", tags=["Sağlık Kurumları"]),
)
class HealthInstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthInstitution.objects.select_related(
        "institution_type", "province", "district",
    ).filter(is_active=True)
    serializer_class = HealthInstitutionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HealthInstitutionFilter
    search_fields = ["name", "address"]


@extend_schema_view(
    list=extend_schema(
        summary="Anlaşmalı sağlık kurumlarını sorgula",
        description=(
            "Ana arama endpoint'i. Şirket, ürün tipi, network, poliçe uygulaması,\n"
            "il, ilçe ve kurum tipine göre filtreleme yapılabilir.\n\n"
            "Her kayıt: kurum bilgileri + şirket + ürün tipi + network + poliçe uygulamaları "
            "+ kapsam notu (`coverage_notes`).\n\n"
            "Yalnızca `is_active=true` olan anlaşmalar döner. Scraper kurumu göremediğinde\n"
            "anlaşmayı pasif yapar; kurum kaydı silinmez."
        ),
        tags=["Sağlık Kurumları"],
        parameters=[
            OpenApiParameter(
                "company__code", str,
                description="Şirket kodu (AXA, HDI, ACIBADEM, TURKIYE, ANADOLU, ALLIANZ, MAPFRE).",
            ),
            OpenApiParameter("product_type__code", str, description="TSS veya OSS."),
            OpenApiParameter("institution__province__plate_code", int, description="İl plaka kodu."),
            OpenApiParameter("institution__district", int, description="İlçe id'si."),
            OpenApiParameter("institution__institution_type__code", str, description="Kurum tipi kodu."),
            OpenApiParameter(
                "networks", str,
                description="Virgülle ayrılmış network id'leri. Herhangi birine sahip anlaşmalar döner.",
            ),
            OpenApiParameter(
                "policy_application", int,
                description="Poliçe uygulaması id'si.",
            ),
            OpenApiParameter(
                "policy_application__service_id", str,
                description="AXA gibi şirketlerin ServiceId'si. Örn: '17' (Sağlığım Tamam TSS).",
            ),
            OpenApiParameter("search", str, description="Kurum adı/adresinde serbest metin arama."),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir kurum anlaşmasının detayı", tags=["Sağlık Kurumları"]),
)
class InstitutionContractViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InstitutionContract.objects.select_related(
        "institution__institution_type",
        "institution__province",
        "institution__district",
        "company",
        "product_type",
    ).prefetch_related(
        "networks__company",
        "networks__product_type",
        "policy_applications__company",
        "policy_applications__product_type",
        "policy_applications__network",
    ).filter(is_active=True).distinct()
    serializer_class = InstitutionContractSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = InstitutionContractFilter
    search_fields = [
        "institution__name",
        "institution__address",
        "coverage_notes",
    ]
