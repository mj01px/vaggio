from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = True

# Se alguem apontar DJANGO_SETTINGS_MODULE para este arquivo em producao, o
# assert estoura alto em vez de vazar estado interno silenciosamente.
assert DEBUG, "development.py carregado com DEBUG=False — abortando."

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config(
        "CORS_ALLOWED_ORIGINS", default="http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

# O front chama a API pelo proxy do Vite, entao o POST do login chega com
# Origin: http://localhost:5173 e host 127.0.0.1:8020. Sem declarar a origem do
# Vite aqui, o Django recusa com 403 "Origin checking failed".
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# debug_toolbar so existe em requirements/development.txt.
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# Nada na frente do Django aqui: o Vite so faz proxy, nao acrescenta cabecalho
# de proxy. Zero manda o DRF ignorar X-Forwarded-For e usar REMOTE_ADDR, que e
# o unico valor que o cliente nao escolhe.
REST_FRAMEWORK["NUM_PROXIES"] = 0  # noqa: F405

# A API renderiza JSON puro em producao; em dev vale a interface navegavel.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
