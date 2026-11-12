(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const pad = (n) => String(n).padStart(2, "0");
  const estado = { token: null, usuario: null, regras: null, recursos: [], ocupadas: [], hora: null };

  // ---------- chamadas à API (mesmo endereço; o ALB roteia pelo prefixo) ----------
  async function api(metodo, caminho, corpo) {
    const cab = { Accept: "application/json" };
    if (corpo) cab["Content-Type"] = "application/json";
    if (estado.token) cab.Authorization = "Bearer " + estado.token;
    const resp = await fetch(caminho, { method: metodo, headers: cab, body: corpo ? JSON.stringify(corpo) : undefined });
    let dados = null;
    try { dados = await resp.json(); } catch (_) { /* corpo vazio */ }
    // Mostra QUAL task atendeu e QUAL versão: é o que as demonstrações de ALB e de deploy exibem.
    $("rodape").textContent =
      `Última chamada: ${metodo} ${caminho.split("?")[0]} → HTTP ${resp.status}` +
      ` · task ${resp.headers.get("X-Task-Id") || "?"} · versão ${resp.headers.get("X-Versao") || "?"}`;
    if (resp.status === 401 && estado.token) sair("Sessão expirada. Entre novamente.");
    return { status: resp.status, ok: resp.ok, dados };
  }

  function aviso(texto, tipo) {
    const el = $("mensagem");
    el.textContent = texto;
    el.className = tipo;
    el.hidden = !texto;
  }

  function descreverErro(r) {
    const d = r.dados || {};
    const detalhe = typeof d.detalhe === "string" ? d.detalhe : JSON.stringify(d.detalhe || "");
    return `HTTP ${r.status} · ${d.erro || "erro"}: ${detalhe}` + (d.restricao ? ` (restrição ${d.restricao})` : "");
  }

  // ---------- sessão ----------
  function guardar() {
    try { sessionStorage.setItem("reservas.sessao", JSON.stringify({ token: estado.token, usuario: estado.usuario })); } catch (_) {}
  }
  function restaurar() {
    try {
      const s = JSON.parse(sessionStorage.getItem("reservas.sessao") || "null");
      if (s && s.token) { estado.token = s.token; estado.usuario = s.usuario; return true; }
    } catch (_) {}
    return false;
  }
  function sair(texto) {
    estado.token = null; estado.usuario = null;
    try { sessionStorage.removeItem("reservas.sessao"); } catch (_) {}
    mostrar();
    aviso(texto || "", texto ? "erro" : "");
  }
  function mostrar() {
    const logado = !!estado.token;
    $("auth").hidden = logado;
    $("app").hidden = !logado;
    $("sessao").hidden = !logado;
    if (logado) $("quem").textContent = `${estado.usuario.nome} (${estado.usuario.papel})`;
  }

  async function entrar(email, senha) {
    const r = await api("POST", "/api/usuarios/login", { email, senha });
    if (!r.ok) return aviso(descreverErro(r), "erro");
    estado.token = r.dados.token; estado.usuario = r.dados.usuario;
    guardar(); mostrar(); aviso("", "");
    await iniciar();
  }

  // ---------- tela de reservas ----------
  function hojeLocal() {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  async function iniciar() {
    const [rr, rc] = await Promise.all([api("GET", "/api/reservas/regras"), api("GET", "/api/recursos/?ativo=true")]);
    if (rr.ok) estado.regras = rr.dados;
    estado.recursos = rc.ok ? rc.dados : [];

    const sel = $("recurso");
    sel.replaceChildren();
    for (const r of estado.recursos) {
      const o = document.createElement("option");
      o.value = r.id; o.textContent = `${r.nome} (${r.capacidade} lugares)`;
      sel.append(o);
    }
    const max = estado.regras ? estado.regras.duracao_max_horas : 1;
    const dur = $("duracao");
    dur.replaceChildren();
    for (let h = 1; h <= max; h++) {
      const o = document.createElement("option");
      o.value = h; o.textContent = h === 1 ? "1 hora" : `${h} horas`;
      dur.append(o);
    }
    if (estado.regras) {
      $("regras").textContent =
        `Regras em vigor: até ${estado.regras.duracao_max_horas} h por reserva, das ${pad(estado.regras.hora_abertura)}h às ` +
        `${pad(estado.regras.hora_fechamento)}h, com até ${estado.regras.dias_antecedencia_max} dias de antecedência.`;
    }
    $("dia").min = $("dia").value = $("dia").value || hojeLocal();
    estado.hora = null;
    await Promise.all([carregarGrade(), carregarMinhas()]);
  }

  async function carregarGrade() {
    const recurso = $("recurso").value, dia = $("dia").value;
    if (!recurso || !dia) return;
    const r = await api("GET", `/api/reservas/disponibilidade?recurso_id=${recurso}&data=${dia}`);
    if (!r.ok) return aviso(descreverErro(r), "erro");
    estado.ocupadas = r.dados.ocupados.map((o) => [Number(o.inicio.slice(11, 13)), Number(o.fim.slice(11, 13))]);
    estado.abre = r.dados.hora_abertura; estado.fecha = r.dados.hora_fechamento;
    desenharGrade();
  }

  function ocupada(h) { return estado.ocupadas.some(([a, b]) => h >= a && h < b); }

  function desenharGrade() {
    const grade = $("grade"), dur = Number($("duracao").value || 1);
    grade.replaceChildren();
    for (let h = estado.abre; h < estado.fecha; h++) {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = `${pad(h)}h`;
      const escolhida = estado.hora !== null && h >= estado.hora && h < estado.hora + dur;
      if (ocupada(h)) { b.className = escolhida ? "conflito" : "ocupado"; }
      else if (escolhida) { b.className = "escolhido"; }
      b.addEventListener("click", () => { estado.hora = h; desenharGrade(); });
      grade.append(b);
    }
    $("reservar").disabled = estado.hora === null;
  }

  async function reservar() {
    const dia = $("dia").value, dur = Number($("duracao").value), fimHora = estado.hora + dur;
    if (fimHora > 23) return aviso("O horário de término precisa ser no mesmo dia.", "erro");
    const r = await api("POST", "/api/reservas/", {
      recurso_id: Number($("recurso").value),
      inicio: `${dia}T${pad(estado.hora)}:00`,
      fim: `${dia}T${pad(fimHora)}:00`,
    });
    if (r.ok) aviso(`Reserva ${r.dados.id} criada (HTTP ${r.status}).`, "ok");
    else aviso(descreverErro(r), "erro");
    estado.hora = null;
    await Promise.all([carregarGrade(), carregarMinhas()]);
  }

  async function carregarMinhas() {
    const r = await api("GET", "/api/reservas/");
    const corpo = $("minhas").tBodies[0];
    corpo.replaceChildren();
    const lista = r.ok ? r.dados : [];
    $("sem-reservas").hidden = lista.length > 0;
    for (const x of lista) {
      const tr = document.createElement("tr");
      const nome = (estado.recursos.find((e) => e.id === x.recurso_id) || {}).nome || `recurso ${x.recurso_id}`;
      for (const texto of [nome, x.inicio.slice(0, 10), `${x.inicio.slice(11, 16)} às ${x.fim.slice(11, 16)}`, x.status]) {
        const td = document.createElement("td"); td.textContent = texto; tr.append(td);
      }
      const acao = document.createElement("td");
      if (x.status === "ativa") {
        const b = document.createElement("button");
        b.className = "sec"; b.textContent = "Cancelar";
        b.addEventListener("click", async () => {
          const c = await api("DELETE", `/api/reservas/${x.id}`);
          aviso(c.ok ? `Reserva ${x.id} cancelada.` : descreverErro(c), c.ok ? "ok" : "erro");
          await Promise.all([carregarGrade(), carregarMinhas()]);
        });
        acao.append(b);
      }
      tr.append(acao); corpo.append(tr);
    }
  }

  // ---------- eventos ----------
  $("form-login").addEventListener("submit", (e) => { e.preventDefault(); entrar($("login-email").value, $("login-senha").value); });
  $("form-cadastro").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = { nome: $("cad-nome").value, email: $("cad-email").value, senha: $("cad-senha").value };
    const r = await api("POST", "/api/usuarios/cadastro", dados);
    if (!r.ok) return aviso(descreverErro(r), "erro");
    await entrar(dados.email, dados.senha);
  });
  $("sair").addEventListener("click", () => sair(""));
  $("recurso").addEventListener("change", () => { estado.hora = null; carregarGrade(); });
  $("dia").addEventListener("change", () => { estado.hora = null; carregarGrade(); });
  $("duracao").addEventListener("change", desenharGrade);
  $("reservar").addEventListener("click", reservar);

  if (restaurar()) { mostrar(); iniciar(); } else { mostrar(); }
})();
