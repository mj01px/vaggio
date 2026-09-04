#!/usr/bin/env python
"""Utilitario de linha de comando do Django."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django nao encontrado. O ambiente virtual esta ativo? "
            "Rode: pip install -r requirements/development.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
