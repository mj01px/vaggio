from django.conf import settings
from django.urls import include, path

# O admin do Django saiu do projeto: tudo que so dava para fazer por la agora
# tem tela e endpoint proprios, sob as mesmas permissoes de cargo do resto.
urlpatterns = [
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.jobs.urls")),
    path("api/v1/", include("apps.pipeline.urls")),
    path("api/v1/", include("apps.collectors.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
