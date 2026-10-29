"""Executa todas as buscas, filtra, descarta o que já foi visto e avisa por e-mail.

Uso:
    python -m robo                 # execução normal
    python -m robo --simular       # mostra o e-mail no terminal em vez de enviar
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import http, notificacao, ranking
from .filtro import aceita
from .fontes import FONTES
from .modelo import Anuncio, Busca, uf_de

RAIZ = Path(__file__).resolve().parent.parent
CACHE_HORAS = 24  # quanto tempo reaproveitar o último resultado de um site que falhou


def ler_cache(caminho: Path, chave: str) -> list[Anuncio] | None:
    try:
        item = json.loads(caminho.read_text())[chave]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None
    idade = datetime.now(timezone.utc) - datetime.fromisoformat(item["data"])
    if idade.total_seconds() > CACHE_HORAS * 3600:
        return None
    return [Anuncio(**a) for a in item["anuncios"]]


def carregar_config(caminho: Path) -> tuple[dict, list[Busca]]:
    config = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    buscas = []
    for b in config.get("buscas", []):
        busca = Busca(**b)
        if busca.uf:
            busca.uf = uf_de(busca.uf) or sys.exit(f"UF inválida na busca '{busca.nome}': {b['uf']}")
        buscas.append(busca)
    return config, buscas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=RAIZ / "config.yaml")
    ap.add_argument("--vistos", type=Path, default=RAIZ / "dados" / "vistos.json")
    ap.add_argument("--simular", action="store_true", help="não envia e-mail, só imprime")
    args = ap.parse_args()

    config, buscas = carregar_config(args.config)
    max_paginas = config.get("max_paginas", 2)
    max_anuncios = config.get("max_anuncios_por_email", 50)

    primeira_vez = not args.vistos.exists()
    vistos: dict[str, str] = json.loads(args.vistos.read_text()) if not primeira_vez else {}

    simular = args.simular or not os.environ.get("SMTP_USUARIO")
    if simular and not args.simular:
        print("AVISO: segredos de e-mail não configurados; rodando em modo simulado.")

    shutil.rmtree(http.DEBUG, ignore_errors=True)
    caminho_cache = args.vistos.parent / "cache.json"
    try:
        cache = json.loads(caminho_cache.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    novos = []
    todos = {}  # todos os anúncios ativos que passam no filtro (para a lista de prioridade)
    erros = []
    relatorio = []
    for busca in buscas:
        for nome_fonte in busca.fontes or config.get("fontes", list(FONTES)):
            http.ultima_resposta = None
            try:
                anuncios = FONTES[nome_fonte](busca, max_paginas)
            except Exception as e:  # uma fonte falhar não pode derrubar as outras
                erros.append(f"{busca.nome}/{nome_fonte}: {e}")
                traceback.print_exc()
                http.salvar_debug(f"{busca.nome}_{nome_fonte}".lower())
                anterior = ler_cache(caminho_cache, f"{busca.nome}/{nome_fonte}")
                relatorio.append({"busca": busca.nome, "fonte": nome_fonte, "erro": f"{type(e).__name__}: {e}"[:300],
                                  "usando_cache": anterior is not None})
                # para a lista de prioridade, usa o último resultado bom (sem gerar avisos de "novo")
                for a in anterior or []:
                    if aceita(a, busca):
                        todos.setdefault(a.chave, (busca.nome, a))
                continue
            cache[f"{busca.nome}/{nome_fonte}"] = {
                "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "anuncios": [vars(a) for a in anuncios],
            }
            aprovados = [a for a in anuncios if aceita(a, busca)]
            print(f"[{busca.nome}] {nome_fonte}: {len(anuncios)} anúncios, {len(aprovados)} passam no filtro")
            relatorio.append({"busca": busca.nome, "fonte": nome_fonte,
                              "anuncios": len(anuncios), "aprovados": len(aprovados)})
            for a in aprovados:
                todos.setdefault(a.chave, (busca.nome, a))
                if a.chave not in vistos:
                    vistos[a.chave] = a.url
                    novos.append((busca.nome, a))

    print(f"{len(novos)} anúncio(s) novo(s). Erros: {len(erros)}")

    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    lista = ranking.calcular(list(todos.values()), {a.chave for _, a in novos})
    (RAIZ / "RANKING.md").write_text(ranking.markdown(lista, agora), encoding="utf-8")

    args.vistos.parent.mkdir(parents=True, exist_ok=True)
    caminho_cache.write_text(json.dumps(cache, ensure_ascii=False))
    (args.vistos.parent / "ultima_execucao.json").write_text(json.dumps({
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ativos": len(todos),
        "novos": len(novos),
        "email_enviado": bool(novos) and not simular,
        "fontes": relatorio,
    }, indent=1, ensure_ascii=False))

    if novos:
        notificacao.enviar(*notificacao.montar(novos, lista, primeira_vez, max_anuncios), simular=simular)

    # em modo simulado não marca nada como visto, para o 1º e-mail real trazer tudo
    if not simular or args.simular:
        args.vistos.write_text(json.dumps(vistos, indent=1, ensure_ascii=False))

    # falha o job só se TODAS as fontes falharem, para você perceber no GitHub
    total = sum(len(b.fontes or config.get("fontes", list(FONTES))) for b in buscas)
    return 1 if erros and len(erros) == total else 0


if __name__ == "__main__":
    sys.exit(main())
