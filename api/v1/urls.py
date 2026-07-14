from rest_framework.routers import DefaultRouter

from .views import (
    CityViewSet,
    DistrictViewSet,
    HealthInstitutionViewSet,
    InstitutionTypeViewSet,
    InsuranceCompanyViewSet,
    NetworkViewSet,
    ProductTypeViewSet,
)

router = DefaultRouter()
router.register("institutions", HealthInstitutionViewSet, basename="institution")
router.register("companies", InsuranceCompanyViewSet, basename="company")
router.register("cities", CityViewSet, basename="city")
router.register("districts", DistrictViewSet, basename="district")
router.register("product-types", ProductTypeViewSet, basename="product-type")
router.register("institution-types", InstitutionTypeViewSet, basename="institution-type")
router.register("networks", NetworkViewSet, basename="network")

urlpatterns = router.urls
