from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    # API base url
    path("api/v1/", include("imagera.api.v1.urls", namespace="api_v1")),
    path("api/v1/", include(router.urls)),
    path("summernote/", include("django_summernote.urls")),
]

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/rylazuxnc/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
      ),
]

urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

handler400 = "imagera.core.views.bad_request"
handler403 = "imagera.core.views.permission_denied"
handler404 = "imagera.core.views.page_not_found"
handler500 = "imagera.core.views.server_error"