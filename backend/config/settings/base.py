"""Configuracao comum a todos os ambientes.

Nunca importe este modulo direto: use config.settings.development ou
config.settings.production, que e o que DJANGO_SETTINGS_MODULE aponta.
"""

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-inseguro-troque-em-producao")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    # Local
    "apps.accounts",
    "apps.core",
    "apps.jobs",
    "apps.pipeline",
    "apps.collectors",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# SQLite por padrao: a ferramenta e de uma pessoa so e precisa rodar sem
# configurar nada. Preencha DB_NAME no .env para trocar por PostgreSQL.
if config("DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"connect_timeout": 10},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "vaggio.sqlite3",
        }
    }

# Login por e-mail. Backend unico de proposito: com o `ModelBackend` ao lado,
# entrar por username continuaria valendo.
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.BackendDeEmail"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    # Sem este, "19283746" passa: nao esta na lista de senhas comuns e tem
    # tamanho de sobra, mas e um teclado numerico e nada mais.
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    # E sem este, a pessoa usa o proprio e-mail como senha, que e a primeira
    # coisa que alguem tenta depois de descobrir o e-mail dela.
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sobrescreva em producao com um caminho aleatorio para reduzir exposicao a scan.

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    # Fechado por padrao: rota nova nasce exigindo login, e abrir e decisao
    # explicita de quem escreve a view. O contrario deixa buraco por esquecimento.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissoes.TemPermissao",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Quantos proxies existem entre o cliente e o Django. E o numero que diz ao
    # DRF ate onde ele pode confiar no X-Forwarded-For.
    #
    # Sem isto o DRF usa o cabecalho INTEIRO como identidade do cliente, e o
    # cabecalho vem de quem chama: trocar ele a cada requisicao dava um balde de
    # contagem novo toda vez, e os tres limites abaixo viravam enfeite. O valor
    # certo depende do deploy, entao cada ambiente declara o seu.
    "NUM_PROXIES": config("NUM_PROXIES", default=0, cast=int),
    # Rota de autenticacao e a unica que da para bater a porta sem sessao, e
    # a unica que manda e-mail para terceiro. Sem limite, "esqueci minha senha"
    # vira ferramenta de encher caixa de entrada dos outros.
    #
    # O `UserRateThrottle` cobre o resto: teto por pessoa, largo o suficiente
    # para nunca esbarrar em uso humano e apertado o suficiente para um laco
    # de script morrer no primeiro minuto.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Teto geral de quem esta logado. Uma triagem intensa faz umas 40
        # requisicoes por minuto; 3000/hora e cinquenta por minuto sustentadas.
        "user": config("THROTTLE_USER", default="3000/hour"),
        # Gerar apresentacao chama o Gemini e leva uns 10 segundos: e cota
        # queimada e worker preso, nao um GET qualquer.
        "pitch": config("THROTTLE_PITCH", default="30/hour"),
        # A coleta leva uns 40 segundos e busca as mesmas fontes toda vez.
        "coleta": config("THROTTLE_COLETA", default="12/hour"),
        # Errar a senha cinco vezes seguidas e humano; cem nao e.
        "login": config("THROTTLE_LOGIN", default="10/min"),
        # Pedir link de recuperacao e acao rara por natureza.
        "recuperacao": config("THROTTLE_RECUPERACAO", default="5/hour"),
        # Conferir o codigo de 2FA erra por dedo trocado, nao por forca bruta:
        # sao seis digitos, entao o limite e o que torna adivinhar inviavel.
        "2fa": config("THROTTLE_2FA", default="10/min"),
    },
}

# ── Cache ─────────────────────────────────────────────────────────────────────
# E onde o DRF guarda a contagem do limite de tentativa. Em memoria serve para
# um processo so, que e o caso do `runserver` e o dos testes. Producao
# sobrescreve: com varios workers do gunicorn, cada um contaria por conta
# propria e o limite real viraria "o numero escrito vezes o numero de workers".
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "vaggio-local",
    }
}

# ── E-mail ────────────────────────────────────────────────────────────────────
# Sem host configurado o backend cai no console: em desenvolvimento o link de
# recuperacao aparece no terminal, e ninguem precisa de SMTP para testar.
#
# A 2525 e alternativa a 587 e costuma passar onde a 587 esta bloqueada.
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = config("EMAIL_PORT", default=2525, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Vaggio <nao-responda@vaggio.local>")
EMAIL_TIMEOUT = 20

# Base dos links que vao no e-mail. E o endereco do FRONT, nao o da API: quem
# clica cai numa tela, nao num endpoint.
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173").rstrip("/")

# Prazo dos links de uso unico, em horas. O convite e mais longo de proposito:
# a pessoa pode nem estar no computador quando a conta e criada.
PRAZO_LINK_SENHA_HORAS = config("PRAZO_LINK_SENHA_HORAS", default=2, cast=int)
PRAZO_LINK_CONVITE_HORAS = config("PRAZO_LINK_CONVITE_HORAS", default=72, cast=int)
PRAZO_LINK_EMAIL_HORAS = config("PRAZO_LINK_EMAIL_HORAS", default=2, cast=int)

# ── Coleta ────────────────────────────────────────────────────────────────────
# Token pessoal do GitHub (escopo publico basta): sem ele a API limita a
# 60 requisicoes/hora, com ele sobe para 5000.
GITHUB_TOKEN = config("GITHUB_TOKEN", default="")
GUPY_API = config("GUPY_API", default="https://employability-portal.gupy.io/api/v1/jobs")

# ── Geracao do "Apresente-se" ─────────────────────────────────────────────────
# Chave do Google AI Studio (aistudio.google.com), free tier. Sem ela o
# `manage.py pitch` para com mensagem clara em vez de estourar no meio.
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-3.7-flash")

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Linha por evento de seguranca: entrada recusada, codigo de 2FA
        # errado, 403 de cargo, conta criada, cargo trocado, 2FA ligado ou
        # desligado. Sai separado do resto para dar para filtrar (`apps.seguranca`)
        # sem caçar no meio do log da aplicacao. Vai para a saida padrao de
        # proposito: quem roda em container ja coleta isso, e arquivo dentro do
        # container e log que some no proximo deploy.
        "apps.seguranca": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Uma linha por requisicao do httpx afogaria a saida do `collect`, que
        # faz dezenas delas. Em WARNING so aparece o que deu errado.
        "httpx": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
