"""Publica eventos de reserva no SQS. Falha ao publicar NÃO derruba a requisição:
a reserva já foi gravada e a notificação é um efeito secundário."""

import json
import logging

from django.conf import settings

log = logging.getLogger("reservas.eventos")
_cliente = None


def _sqs():
    global _cliente
    if _cliente is None:
        import boto3
        from botocore.config import Config

        _cliente = boto3.client(
            "sqs",
            region_name=settings.AWS_REGION,
            config=Config(connect_timeout=2, read_timeout=3, retries={"max_attempts": 2}),
        )
    return _cliente


def publicar(tipo, reserva, usuario):
    corpo = {
        "evento": tipo,
        "reserva": reserva,
        "usuario": {"id": usuario.id, "nome": usuario.nome, "email": usuario.email},
    }
    if not settings.SQS_URL:
        log.info("SQS_URL vazio; evento %s não enviado: %s", tipo, json.dumps(corpo, ensure_ascii=False))
        return False
    try:
        _sqs().send_message(QueueUrl=settings.SQS_URL, MessageBody=json.dumps(corpo, ensure_ascii=False))
        return True
    except Exception:  # nota:qualquer falha aqui é só registrada
        log.exception("falha ao publicar %s no SQS", tipo)
        return False
