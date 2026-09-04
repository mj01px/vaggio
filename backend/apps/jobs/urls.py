from rest_framework.routers import SimpleRouter

from .views import JobViewSet

# SimpleRouter, e nao DefaultRouter: tres routers montados no mesmo prefixo
# registrariam tres raizes de API concorrentes e o conversor de sufixo do
# DRF tres vezes. A raiz util aqui e /api/v1/health/.
router = SimpleRouter()
router.register("jobs", JobViewSet, basename="job")

urlpatterns = router.urls
