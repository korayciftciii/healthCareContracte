from django.urls import re_path
from .consumers import LogStreamConsumer

websocket_urlpatterns = [
    re_path(r"^ws/admin/log-stream/$", LogStreamConsumer.as_asgi()),
]
