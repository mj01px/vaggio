from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = config("SECRET_KEY")

# `check --deploy` so avisa (W009) sobre chave fraca, e aviso nao para deploy
# nenhum. Esta chave assina os tokens de recuperacao de senha e o codigo de
# troca de e-mail: chave adivinhavel e link de reset forjado. Entao aqui e
# assert, e nao aviso.
#
# O que se mede e resistencia a chute, e nao comprimento: 40 caracteres com
# variedade cobrem os dois jeitos normais de gerar uma, e nenhum deles e o
# limite de 50 do aviso do Django.
#
#   get_random_secret_key() do Django   50 caracteres de um alfabeto de 50
#   `generateValue: true` do Render     44 caracteres de base64 (256 bits)
#
# Os dois passam de 200 bits. O que nao passa daqui e chave digitada a mao,
# que e o caso real que isto existe para pegar.
_VARIEDADE_MINIMA = 12
assert len(SECRET_KEY) >= 40 and len(set(SECRET_KEY)) >= _VARIEDADE_MINIMA, (
    "SECRET_KEY de producao fraca: precisa de pelo menos 40 caracteres e "
    f"{_VARIEDADE_MINIMA} caracteres distintos. No Render, use `generateValue`. "
    "Fora dele: python -c \"from django.core.management.utils import "
    "get_random_secret_key as g; print(g())\""
)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# O Render publica o hostname do servico nesta variavel, e ele muda quando o
# servico e recriado. Acrescentar sozinho evita o DisallowedHost em toda
# requisicao por causa de um nome que ninguem lembrou de copiar para o painel.
#
# Sem assert aqui de proposito: a variavel nao existe durante o BUILD, so em
# execucao, e `migrate` e `collectstatic` rodam no build. Exigir a lista cheia
# ali derrubava o deploy antes de o servico existir, que e justamente quando
# ainda nao da para saber o endereco dele. Lista vazia em producao nao passa
# silenciosa: o Django recusa toda requisicao com DisallowedHost, alto e claro.
_hostname_do_render = config("RENDER_EXTERNAL_HOSTNAME", default="")
if _hostname_do_render and _hostname_do_render not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_hostname_do_render)

# Quantos saltos de proxy existem entre o cliente e o Django. E o numero que
# diz ao DRF ate onde da para confiar no X-Forwarded-For, que e a identidade que
# o limite de tentativa usa. Errar para mais e deixar o cliente escolher a
# propria identidade; errar para menos e contar todo mundo como um IP so.
#
#     1  hospedagem com um proxy na frente (Render, Fly, Railway, Heroku)
#     2  o mesmo, com Cloudflare na frente dele
#     0  Django exposto direto, sem proxy nenhum
#
# Como conferir em vez de chutar: suba, mande uma requisicao com um
# `X-Forwarded-For: 1.2.3.4` inventado e veja se o limite de tentativa ainda
# pega. Se parar de pegar, o numero esta alto demais.
REST_FRAMEWORK["NUM_PROXIES"] = config("NUM_PROXIES", default=1, cast=int)  # noqa: F405

# Um cache que os workers compartilham, que e onde vive a contagem do limite de
# tentativa. Em arquivo por padrao porque nao exige servico novo nem
# `createcachetable` esquecido no deploy, e todos os workers do mesmo processo
# de deploy enxergam o mesmo diretorio.
#
# Em hospedagem com disco efemero (Render e afins) isso zera a cada deploy e a
# cada hibernacao, o que enfraquece o limite mas nao o quebra: quem esta no meio
# de uma tentativa de forca bruta perde o balde junto. Com Redis a mao, aponte
# CACHE_BACKEND para django.core.cache.backends.redis.RedisCache e
# CACHE_LOCATION para a URL dele, que resolve os dois problemas.
CACHES = {
    "default": {
        "BACKEND": config(
            "CACHE_BACKEND",
            default="django.core.cache.backends.filebased.FileBasedCache",
        ),
        "LOCATION": config("CACHE_LOCATION", default=str(BASE_DIR / ".cache")),  # noqa: F405
        "TIMEOUT": 3600,
    }
}

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
X_FRAME_OPTIONS = "DENY"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
