"""Worker `notificacoes`: consome a fila reservas-eventos e "avisa" o usuário.

Sem porta e sem ALB. O aviso é uma linha de log (visível no CloudWatch Logs); se
SNS_TOPIC_ARN estiver definido, também é publicado no SNS.

Mensagens que falham voltam para a fila quando o visibility timeout vence; depois de
3 recebimentos sem sucesso a própria fila as move para a DLQ (redrive policy da stack).
"""

import json
import logging
import os
import signal
import sys
import time

log = logging.getLogger("notificacoes")
parar = False


def _ao_receber_sinal(signum, _frame):
    global parar
    parar = True
    log.info("sinal %s recebido; encerrando depois do lote atual", signum)


def montar_aviso(corpo: str) -> str:
    """Transforma o evento JSON na frase de notificação. Levanta exceção se o evento for inválido."""
    evento = json.loads(corpo)
    reserva, usuario = evento["reserva"], evento["usuario"]
    quando = f"{reserva['inicio'][:10]} das {reserva['inicio'][11:16]} às {reserva['fim'][11:16]}"
    if evento["evento"] == "reserva.criada":
        return f"Olá, {usuario['nome']}: sua reserva {reserva['id']} (recurso {reserva['recurso_id']}) em {quando} foi confirmada."
    if evento["evento"] == "reserva.cancelada":
        return f"Olá, {usuario['nome']}: sua reserva {reserva['id']} (recurso {reserva['recurso_id']}) em {quando} foi cancelada."
    raise ValueError(f"evento desconhecido: {evento['evento']}")


def processar_lote(sqs, url, sns=None, topico=None):
    """Recebe até 10 mensagens e apaga só as que foram processadas."""
    resposta = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=20)
    feitas = 0
    for mensagem in resposta.get("Messages", []):
        try:
            aviso = montar_aviso(mensagem["Body"])
            log.info("NOTIFICACAO %s", aviso)
            if sns and topico:
                sns.publish(TopicArn=topico, Subject="Reservas da Faculdade", Message=aviso)
            sqs.delete_message(QueueUrl=url, ReceiptHandle=mensagem["ReceiptHandle"])
            feitas += 1
        except Exception:  # nota: a mensagem fica na fila e será reentregue
            log.exception("falha ao processar a mensagem %s; ela voltará à fila", mensagem.get("MessageId"))
    return feitas


def main():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    url = os.environ.get("SQS_URL")
    if not url:
        log.error("defina SQS_URL")
        sys.exit(1)
    import boto3

    regiao = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    sqs = boto3.client("sqs", region_name=regiao)
    topico = os.environ.get("SNS_TOPIC_ARN")
    sns = boto3.client("sns", region_name=regiao) if topico else None

    signal.signal(signal.SIGTERM, _ao_receber_sinal)  
    signal.signal(signal.SIGINT, _ao_receber_sinal)
    log.info("worker iniciado; fila %s", url)
    while not parar:
        try:
            processar_lote(sqs, url, sns, topico)
        except Exception:  # nota: falha de rede/credencial = tenta de novo
            log.exception("erro ao consultar a fila; nova tentativa em instantes")
            for _ in range(50):
                if parar:
                    break
                time.sleep(0.1)
    log.info("worker encerrado")


if __name__ == "__main__":
    main()
