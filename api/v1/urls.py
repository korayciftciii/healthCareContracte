from rest_framework.routers import DefaultRouter

from .views import (
    ProvinceViewSet,
    DistrictViewSet,
    HealthInstitutionViewSet,
    InstitutionContractViewSet,
    InstitutionTypeViewSet,
    InsuranceCompanyViewSet,
    NetworkViewSet,
    PolicyApplicationViewSet,
    ProductTypeViewSet,
)

router = DefaultRouter()
router.register("institutions", HealthInstitutionViewSet, basename="institution")
router.register("contracts", InstitutionContractViewSet, basename="contract")
router.register("companies", InsuranceCompanyViewSet, basename="company")
router.register("provinces", ProvinceViewSet, basename="province")
router.register("districts", DistrictViewSet, basename="district")
router.register("product-types", ProductTypeViewSet, basename="product-type")
router.register("institution-types", InstitutionTypeViewSet, basename="institution-type")
router.register("networks", NetworkViewSet, basename="network")
router.register("policy-applications", PolicyApplicationViewSet, basename="policy-application")

urlpatterns = router.urls
