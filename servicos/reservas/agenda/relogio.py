from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings


def agora():
    """Retorna o horário atual da faculdade, sem timezone (timestamp)."""
    return datetime.now(ZoneInfo(settings.FACULDADE_TZ)).replace(tzinfo=None)
