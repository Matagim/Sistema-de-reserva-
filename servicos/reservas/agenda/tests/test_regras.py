import unittest
from datetime import datetime

from agenda.regras import RegraViolada, Regras, validar_periodo

REGRAS = Regras()  # padrão: 4h, 07h-22h, 14 dias
AGORA = datetime(2026, 11, 3, 10, 30)


def d(dia, hora):
    return datetime(2026, 11, dia, hora, 0)


class ValidarPeriodoTest(unittest.TestCase):
    def violacao(self, inicio, fim, regras=REGRAS):
        with self.assertRaises(RegraViolada) as ctx:
            validar_periodo(inicio, fim, AGORA, regras)
        return ctx.exception.codigo

    def test_reserva_valida(self):
        validar_periodo(d(4, 14), d(4, 16), AGORA, REGRAS)

    def test_limites_da_janela_sao_validos(self):
        validar_periodo(d(4, 7), d(4, 9), AGORA, REGRAS)
        validar_periodo(d(4, 20), d(4, 22), AGORA, REGRAS)

    def test_fim_antes_do_inicio(self):
        self.assertEqual(self.violacao(d(4, 16), d(4, 14)), "periodo_invalido")
        self.assertEqual(self.violacao(d(4, 14), d(4, 14)), "periodo_invalido")

    def test_exige_hora_cheia(self):
        self.assertEqual(self.violacao(datetime(2026, 11, 4, 14, 30), d(4, 16)), "periodo_invalido")

    def test_duracao_maxima(self):
        validar_periodo(d(4, 10), d(4, 14), AGORA, REGRAS)  # 4h ainda vale
        self.assertEqual(self.violacao(d(4, 10), d(4, 15)), "duracao_invalida")

    def test_duracao_maxima_vem_da_regra(self):
        regras = Regras(duracao_max_horas=2)
        self.assertEqual(self.violacao(d(4, 10), d(4, 13), regras), "duracao_invalida")

    def test_fora_da_janela(self):
        self.assertEqual(self.violacao(d(4, 6), d(4, 8)), "fora_da_janela")
        self.assertEqual(self.violacao(d(4, 21), d(4, 23)), "fora_da_janela")

    def test_precisa_terminar_no_mesmo_dia(self):
        self.assertEqual(self.violacao(d(4, 21), d(5, 1)), "fora_da_janela")

    def test_no_passado(self):
        self.assertEqual(self.violacao(d(3, 8), d(3, 9)), "no_passado")
        self.assertEqual(self.violacao(d(3, 10), d(3, 11)), "no_passado")  # 10:00 < 10:30

    def test_proxima_hora_do_mesmo_dia_vale(self):
        validar_periodo(d(3, 11), d(3, 12), AGORA, REGRAS)

    def test_antecedencia_maxima(self):
        validar_periodo(d(17, 10), d(17, 11), AGORA, REGRAS)  # exatamente 14 dias
        self.assertEqual(self.violacao(d(18, 10), d(18, 11)), "antecedencia_excedida")


class RegrasDoAmbienteTest(unittest.TestCase):
    def test_padroes(self):
        self.assertEqual(Regras.do_ambiente({}), Regras())

    def test_le_variaveis(self):
        regras = Regras.do_ambiente({"DURACAO_MAX_HORAS": "2", "HORA_ABERTURA": "8"})
        self.assertEqual((regras.duracao_max_horas, regras.hora_abertura), (2, 8))


if __name__ == "__main__":
    unittest.main()
