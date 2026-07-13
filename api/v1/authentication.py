from django.conf import settings
from django.utils.crypto import constant_time_compare
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header


class ServiceAccount:
    """Represents the single Next.js backend client authenticated via master token."""

    is_authenticated = True
    is_active = True
    pk = None
    id = None

    def __str__(self):
        return "nextjs-service-account"


class StaticBearerTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        token = parts[1].strip()
        if not token or not constant_time_compare(token, settings.NEXTJS_MASTER_TOKEN):
            raise exceptions.AuthenticationFailed("Invalid token.")

        return (ServiceAccount(), token)

    def authenticate_header(self, request):
        return self.keyword


class StaticBearerTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """Swagger UI'da "Authorize" butonunun görünmesini ve tek bir statik
    Bearer token ile "Try it out" yapılabilmesini sağlar."""

    target_class = StaticBearerTokenAuthentication
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "Next.js backend'inin kullandığı sabit master token "
                "(NEXTJS_MASTER_TOKEN ortam değişkeni ile aynı)."
            ),
        }
