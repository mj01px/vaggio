from rest_framework.routers import SimpleRouter

from .views import CollectionRunViewSet

router = SimpleRouter()
router.register("collections", CollectionRunViewSet, basename="collection")

urlpatterns = router.urls
