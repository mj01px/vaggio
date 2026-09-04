"""Envelope unico de erro da API.

Toda falha sai como { "error": { "code", "message", "details" } }, para o front
ter um formato so para tratar em vez de adivinhar entre `detail`, lista e dict.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Excecao nao tratada", exc_info=exc)
        return Response(
            {"error": {"code": "INTERNAL_ERROR", "message": "Erro inesperado.", "details": []}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response.data = {
        "error": {
            "code": _error_code(exc, response),
            "message": _message(response.data),
            "details": _details(response.data),
        }
    }
    return response


def _error_code(exc, response) -> str:
    code = getattr(exc, "default_code", None)
    if code:
        return str(code).upper()
    return _CODES.get(response.status_code, "ERROR")


def _message(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        for errors in data.values():
            found = _first_string(errors)
            if found:
                return found
    found = _first_string(data)
    return found or "Requisicao invalida."


def _first_string(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list | tuple):
        for item in value:
            found = _first_string(item)
            if found:
                return found
    if isinstance(value, dict):
        for item in value.values():
            found = _first_string(item)
            if found:
                return found
    return ""


def _details(data) -> list[dict]:
    if not isinstance(data, dict) or "detail" in data:
        return []
    return [
        {"field": field, "message": _first_string(errors)}
        for field, errors in data.items()
        if _first_string(errors)
    ]
