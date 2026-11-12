import json
import unittest

import worker

CRIADA = {
    "evento": "reserva.criada",
    "reserva": {"id": 7, "recurso_id": 3, "inicio": "2026-11-03T14:00:00", "fim": "2026-11-03T16:00:00"},
    "usuario": {"id": 1, "nome": "Aluno Demo", "email": "aluno@faculdade.local"},
}


class FakeSQS:
    def __init__(self, corpos):
        self.mensagens = [{"MessageId": str(i), "ReceiptHandle": f"h{i}", "Body": c} for i, c in enumerate(corpos)]
        self.apagadas = []

    def receive_message(self, **_):
        return {"Messages": self.mensagens}

    def delete_message(self, QueueUrl, ReceiptHandle):
        self.apagadas.append(ReceiptHandle)


class MontarAvisoTest(unittest.TestCase):
    def test_criada(self):
        texto = worker.montar_aviso(json.dumps(CRIADA))
        self.assertIn("Aluno Demo", texto)
        self.assertIn("confirmada", texto)
        self.assertIn("2026-11-03 das 14:00 às 16:00", texto)

    def test_cancelada(self):
        self.assertIn("cancelada", worker.montar_aviso(json.dumps({**CRIADA, "evento": "reserva.cancelada"})))

    def test_evento_desconhecido_falha(self):
        with self.assertRaises(ValueError):
            worker.montar_aviso(json.dumps({**CRIADA, "evento": "outra.coisa"}))


class ProcessarLoteTest(unittest.TestCase):
    def test_apaga_so_o_que_deu_certo(self):
        sqs = FakeSQS([json.dumps(CRIADA), "isto não é json", json.dumps({**CRIADA, "evento": "x"})])
        with self.assertLogs("notificacoes", level="ERROR"):
            feitas = worker.processar_lote(sqs, "fila")
        self.assertEqual(feitas, 1)
        self.assertEqual(sqs.apagadas, ["h0"])  # as inválidas ficam na fila (e vão para a DLQ)


if __name__ == "__main__":
    unittest.main()
