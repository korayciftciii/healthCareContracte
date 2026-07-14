from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from companies.models import InsuranceCompany, Network
from geo.models import City, District
from institutions.models import HealthInstitution
from products.models import InstitutionType, ProductType

from .filters import HealthInstitutionFilter
from .serializers import (
    CitySerializer,
    DistrictSerializer,
    HealthInstitutionSerializer,
    InstitutionTypeSerializer,
    InsuranceCompanySerializer,
    NetworkSerializer,
    ProductTypeSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="Sigorta şirketlerini listele",
        description="Sistemde tanımlı 7 sigorta şirketini (AXA, HDI, Acıbadem, Türkiye, "
        "Anadolu, Allianz, Mapfre) döner. Dropdown/filtre doldurmak için kullanılır.",
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
        description="Türkiye'nin 81 ilini plaka koduyla birlikte döner "
        "(tamamlayicisaglik.com'daki cityId, plaka koduyla birebir aynıdır).",
        tags=["Referans Veriler"],
    ),
    retrieve=extend_schema(summary="Tek bir ilin detayı", tags=["Referans Veriler"]),
)
class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="İlçeleri listele",
        description="`?city=<il id>` ile belirli bir ile ait ilçeleri filtreleyebilirsin.",
        tags=["Referans Veriler"],
        parameters=[
            OpenApiParameter(
                "city", int, description="İl id'sine göre filtrele (city/ ucundaki `id` alanı)."
            ),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir ilçenin detayı", tags=["Referans Veriler"]),
)
class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.select_related("city").all()
    serializer_class = DistrictSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["city"]
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
        description="Hastane, Tıp Merkezi, Diş Hekimi, Optik, Medikal vb. — 9 kurum türü.",
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
        summary="Network'leri listele",
        description="Bir sigorta şirketinin bir ürün tipi (TSS/ÖSS) içindeki alt-kapsam "
        "tier'ları (örn. AXA TSS için 'Sağlığım Tamam' / 'Tutumlu'). Aynı şirketin TSS "
        "ve ÖSS network'leri tamamen farklıdır. `?company__code=` ve `?product_type__code=` "
        "ile filtrelenir. Bazı şirketlerin (örn. Mapfre) hiç network'ü yoktur.",
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
        summary="Anlaşmalı sağlık kurumlarını sorgula",
        description=(
            "Sigorta şirketi, il, ilçe, ürün tipi ve kurum tipine göre filtrelenebilen "
            "anlaşmalı kurum listesi. Bu, sistemin ana endpoint'idir — Next.js frontend'i "
            "büyük olasılıkla en çok bunu kullanacak.\n\n"
            "Adres/telefon/koordinat bilgisi **yoktur** (kaynak site bu bilgileri "
            "sağlamıyor) — sadece isim, il/ilçe ve kurum tipi bilgisi vardır."
        ),
        tags=["Sağlık Kurumları"],
        parameters=[
            OpenApiParameter(
                "company__code", str,
                description="Şirket kodu (AXA, HDI, ACIBADEM, TURKIYE, ANADOLU, ALLIANZ, MAPFRE).",
            ),
            OpenApiParameter(
                "city__plate_code", int, description="İl plaka kodu (örn. İstanbul için 34)."
            ),
            OpenApiParameter("district", int, description="İlçe id'si (districts/ endpoint'inden)."),
            OpenApiParameter("product_type__code", str, description="TSS veya OSS."),
            OpenApiParameter(
                "institution_type__code", str,
                description="HASTANE, TIP_MERKEZI, DIS, OPTIK, MEDIKAL, FIZIK_TEDAVI, "
                "TANI_GORUNTULEME, EVDE_BAKIM, DOKTOR.",
            ),
            OpenApiParameter(
                "networks", str,
                description="Network id'sine göre filtrele (networks/ endpoint'inden gelen `id`). "
                "Virgülle ayrılmış birden fazla id kabul eder (örn. `networks=25,26`) — herhangi "
                "birine sahip kurumlar döner. Şirket seçilmemişse anlamsızdır; company__code ile "
                "birlikte kullanılmalı.",
            ),
            OpenApiParameter("search", str, description="Kurum adı/adresinde serbest metin arama."),
        ],
    ),
    retrieve=extend_schema(summary="Tek bir sağlık kurumunun detayı", tags=["Sağlık Kurumları"]),
)
class HealthInstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthInstitution.objects.select_related(
        "company", "product_type", "institution_type", "city", "district"
    ).prefetch_related("networks").filter(is_active=True).distinct()
    serializer_class = HealthInstitutionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HealthInstitutionFilter
    search_fields = ["name", "address"]
