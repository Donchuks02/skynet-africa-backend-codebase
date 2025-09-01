from rest_framework.routers import DefaultRouter
from .views import ServiceInstanceViewSet

router = DefaultRouter()
router.register(r"services", ServiceInstanceViewSet, basename="service-instance")

urlpatterns = router.urls
