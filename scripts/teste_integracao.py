#!/usr/bin/env python3
"""Teste ponta a ponta contra o sistema em execução (local ou na AWS).

    BASE_URL=http://localhost:8000 python scripts/teste_integracao.py

Precisa dos usuários do seed (SEED_SENHA, padrão demo12345). Cria um recurso próprio e
cancela suas reservas no fim, então pode rodar quantas vezes quiser.
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

BASE = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
SENHA = os.environ.get("SEED_SENHA", "demo12345")
falhas = []


def req(metodo, caminho, corpo=None, token=None):
    cab = {"Accept": "application/json"}
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode()
        cab["Content-Type"] = "application/json"
    if token:
        cab["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + caminho, data=dados, headers=cab, method=metodo)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            texto, status, h = resp.read(), resp.status, resp.headers
    except urllib.error.HTTPError as e:
        texto, status, h = e.read(), e.code, e.headers
    try:
        return status, json.loads(texto), h
    except ValueError:
        return status, texto.decode(errors="replace"), h


def confere(descricao, condicao, extra=""):
    print(("  ok   " if condicao else "  FALHA ") + descricao + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        falhas.append(descricao)


def login(email):
    status, dados, _ = req("POST", "/api/usuarios/login", {"email": email, "senha": SENHA})
    assert status == 200, f"login de {email} falhou: {status} {dados}"
    return dados["token"]


def horario(dias, hora):
    return (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d") + f"T{hora:02d}:00"


def main():
    print(f"alvo: {BASE}\n\n[saúde]")
    for caminho in ("/health", "/api/usuarios/health", "/api/recursos/health", "/api/reservas/health"):
        status, dados, h = req("GET", caminho)
        confere(f"GET {caminho} -> 200", status == 200, f"{status} {dados}")
    confere("X-Task-Id presente", bool(h.get("X-Task-Id")))

    print("\n[usuarios]")
    email = f"teste{int(time.time() * 1000)}@faculdade.local"
    s, d, _ = req("POST", "/api/usuarios/cadastro", {"nome": "Teste", "email": email, "senha": "senha-longa-1"})
    confere("cadastro -> 201 como aluno", s == 201 and d.get("papel") == "aluno", f"{s} {d}")
    s, d, _ = req("POST", "/api/usuarios/cadastro", {"nome": "Teste", "email": email, "senha": "senha-longa-1"})
    confere("e-mail repetido -> 409", s == 409 and d.get("erro") == "email_ja_cadastrado", f"{s} {d}")
    s, d, _ = req("POST", "/api/usuarios/cadastro", {"nome": "X", "email": "x@x.com", "senha": "curta"})
    confere("senha curta -> 400", s == 400, f"{s} {d}")
    s, d, _ = req("POST", "/api/usuarios/login", {"email": email, "senha": "errada"})
    confere("senha errada -> 401", s == 401, f"{s} {d}")

    aluno, aluno2 = login("aluno@faculdade.local"), login("aluno2@faculdade.local")
    admin = login("admin@faculdade.local")

    print("\n[recursos]")
    s, d, _ = req("GET", "/api/recursos")
    confere("lista pública (sem barra final) -> 200", s == 200 and len(d) >= 1, f"{s}")
    s, d, _ = req("GET", "/api/recursos/999999")
    confere("recurso inexistente -> 404", s == 404, f"{s} {d}")
    novo = {"nome": f"Sala Teste {int(time.time())}", "tipo": "sala", "capacidade": 20, "local": "Bloco T"}
    s, _, _ = req("POST", "/api/recursos/", novo)
    confere("criar sem token -> 401", s == 401, str(s))
    s, _, _ = req("POST", "/api/recursos/", novo, aluno)
    confere("criar como aluno -> 403", s == 403, str(s))
    s, d, _ = req("POST", "/api/recursos/", novo, admin)
    confere("criar como admin -> 201", s == 201, f"{s} {d}")
    rid = d["id"]
    s, d, _ = req("POST", "/api/recursos/", {**novo, "capacidade": 0}, admin)
    confere("capacidade 0 -> 400", s == 400, f"{s} {d}")
    s, d, _ = req("POST", "/api/recursos/", {**novo, "tipo": "garagem"}, admin)
    confere("tipo inválido -> 400", s == 400, f"{s} {d}")
    s, d, _ = req("POST", "/api/recursos/", {**novo, "nome": "Sala Inativa", "ativo": False}, admin)
    inativo = d["id"]

    print("\n[reservas: regras de negócio]")
    def reservar(token, recurso, dias, h1, h2):
        return req("POST", "/api/reservas/", {"recurso_id": recurso, "inicio": horario(dias, h1), "fim": horario(dias, h2)}, token)

    s, d, _ = req("GET", "/api/reservas/regras")
    confere("GET /regras -> 200", s == 200 and "duracao_max_horas" in d, f"{s}")
    s, d, _ = req("POST", "/api/reservas/", {"recurso_id": rid, "inicio": horario(2, 10), "fim": horario(2, 11)})
    confere("sem token -> 401", s == 401, str(s))
    s, d, _ = reservar(aluno, rid, 2, 10, 15)
    confere("5 horas -> 400 duracao_invalida", s == 400 and d.get("erro") == "duracao_invalida", f"{s} {d}")
    s, d, _ = reservar(aluno, rid, 2, 5, 7)
    confere("antes das 07h -> 400 fora_da_janela", s == 400 and d.get("erro") == "fora_da_janela", f"{s} {d}")
    s, d, _ = reservar(aluno, rid, -1, 10, 11)
    confere("no passado -> 400", s == 400 and d.get("erro") == "no_passado", f"{s} {d}")
    s, d, _ = reservar(aluno, rid, 30, 10, 11)
    confere("30 dias à frente -> 400", s == 400 and d.get("erro") == "antecedencia_excedida", f"{s} {d}")
    s, d, _ = req("POST", "/api/reservas/", {"recurso_id": rid, "inicio": "2030-01-01T10:00:00Z", "fim": "2030-01-01T11:00:00Z"}, aluno)
    confere("horário com fuso -> 400", s == 400, f"{s} {d}")
    s, d, _ = reservar(aluno, 999999, 2, 10, 11)
    confere("recurso inexistente -> 404", s == 404, f"{s} {d}")
    s, d, _ = reservar(aluno, inativo, 2, 10, 11)
    confere("recurso inativo -> 409 recurso_inativo", s == 409 and d.get("erro") == "recurso_inativo", f"{s} {d}")

    print("\n[reservas: conflito de horário no banco]")
    criadas = []
    s, d, _ = reservar(aluno, rid, 3, 14, 16)
    confere("14h-16h -> 201", s == 201, f"{s} {d}")
    criadas.append((aluno, d.get("id")))
    primeira = d.get("id")
    s, d, _ = reservar(aluno2, rid, 3, 15, 17)
    confere("15h-17h (sobreposição parcial) -> 409", s == 409 and d.get("erro") == "horario_ocupado", f"{s} {d}")
    confere("409 cita a restrição do banco", d.get("restricao") == "reservas_sem_sobreposicao", str(d))
    s, d, _ = reservar(aluno2, rid, 3, 14, 15)
    confere("14h-15h (dentro da existente) -> 409", s == 409, f"{s} {d}")
    s, d, _ = reservar(aluno2, rid, 3, 16, 18)
    confere("16h-18h (encostando no fim) -> 201", s == 201, f"{s} {d}")
    criadas.append((aluno2, d.get("id")))
    s, d, _ = req("GET", f"/api/reservas/disponibilidade?recurso_id={rid}&data={horario(3, 0)[:10]}")
    confere("disponibilidade lista 2 intervalos", s == 200 and len(d["ocupados"]) == 2, f"{s} {d}")
    s, d, _ = req("GET", "/api/reservas/", token=aluno)
    confere("minhas reservas contém a 14h-16h", s == 200 and any(r["id"] == primeira for r in d), f"{s}")

    print("\n[reservas: cancelamento]")
    s, d, _ = req("DELETE", f"/api/reservas/{primeira}", token=aluno2)
    confere("outro aluno cancelando -> 403", s == 403, f"{s} {d}")
    s, d, _ = req("DELETE", "/api/reservas/999999", token=aluno)
    confere("reserva inexistente -> 404", s == 404, f"{s} {d}")
    s, d, _ = req("DELETE", f"/api/reservas/{primeira}", token=aluno)
    confere("dono cancela -> 200 cancelada", s == 200 and d.get("status") == "cancelada", f"{s} {d}")
    s, d, _ = req("DELETE", f"/api/reservas/{primeira}", token=aluno)
    confere("cancelar de novo é idempotente -> 200", s == 200, f"{s} {d}")
    s, d, _ = reservar(aluno2, rid, 3, 14, 16)
    confere("horário liberado pode ser reservado -> 201", s == 201, f"{s} {d}")
    criadas.append((aluno2, d.get("id")))
    outro, _, _ = (None, None, None)

    print("\n[concorrência: várias requisições simultâneas no mesmo horário]")
    for rodada in range(3):
        n = 8
        barreira = threading.Barrier(n)
        dia, hora = 4 + rodada, 9 + rodada

        def disparar(i):
            barreira.wait()
            return reservar(aluno if i % 2 else aluno2, rid, dia, hora, hora + 1)

        with ThreadPoolExecutor(max_workers=n) as pool:
            respostas = list(pool.map(disparar, range(n)))
        status = sorted(r[0] for r in respostas)
        confere(f"rodada {rodada + 1}: {n} simultâneas -> exatamente um 201 e {n - 1} x 409", status == [201] + [409] * (n - 1), str(status))
        for r in respostas:
            if r[0] == 201:
                criadas.append((aluno, r[1]["id"]))

    print("\n[limpeza]")
    for token, id_ in criadas:
        if id_:
            req("DELETE", f"/api/reservas/{id_}", token=admin)
    req("PATCH", f"/api/recursos/{rid}", {"ativo": False}, admin)
    print("  reservas de teste canceladas e recurso de teste desativado")

    print()
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for f in falhas:
            print(" -", f)
        sys.exit(1)
    print("tudo certo")


if __name__ == "__main__":
    main()
