"""Executa todas as buscas, filtra, descarta o que já foi visto e avisa no WhatsApp.

Uso:
    python -m robo                 # execução normal
    python -m robo --simular       # mostra as mensagens no terminal em vez de enviar
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import yaml

from . import whatsapp
from .filtro import aceita
from .fontes import FONTES
from .modelo import Busca, uf_de

RAIZ = Path(__file__).resolve().parent.parent


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
    ap.add_argument("--simular", action="store_true", help="não envia WhatsApp, só imprime")
    args = ap.parse_args()

    config, buscas = carregar_config(args.config)
    max_paginas = config.get("max_paginas", 2)
    max_msgs = config.get("max_mensagens_por_execucao", 10)

    primeira_vez = not args.vistos.exists()
    vistos: dict[str, str] = json.loads(args.vistos.read_text()) if not primeira_vez else {}

    novos = []
    erros = []
    for busca in buscas:
        for nome_fonte in busca.fontes or config.get("fontes", list(FONTES)):
            try:
                anuncios = FONTES[nome_fonte](busca, max_paginas)
            except Exception as e:  # uma fonte falhar não pode derrubar as outras
                erros.append(f"{busca.nome}/{nome_fonte}: {e}")
                traceback.print_exc()
                continue
            aprovados = [a for a in anuncios if aceita(a, busca)]
            print(f"[{busca.nome}] {nome_fonte}: {len(anuncios)} anúncios, {len(aprovados)} passam no filtro")
            for a in aprovados:
                if a.chave not in vistos:
                    vistos[a.chave] = a.url
                    novos.append((busca.nome, a))

    print(f"{len(novos)} anúncio(s) novo(s). Erros: {len(erros)}")

    if primeira_vez and config.get("silenciar_primeira_execucao", True):
        print("Primeira execução: anúncios atuais registrados sem notificar.")
        if novos:
            whatsapp.enviar(
                f"🤖 Robô de carros ativado! {len(novos)} anúncios atuais registrados. "
                "A partir de agora você recebe só os novos.",
                args.simular,
            )
    else:
        for nome_busca, a in novos[:max_msgs]:
            whatsapp.enviar(whatsapp.formatar(a, nome_busca), args.simular)
        if len(novos) > max_msgs:
            whatsapp.enviar(f"…e mais {len(novos) - max_msgs} anúncio(s) novo(s). Refine os filtros!", args.simular)

    args.vistos.parent.mkdir(parents=True, exist_ok=True)
    args.vistos.write_text(json.dumps(vistos, indent=1, ensure_ascii=False))

    # falha o job só se TODAS as fontes falharem, para você perceber no GitHub
    total = sum(len(b.fontes or config.get("fontes", list(FONTES))) for b in buscas)
    return 1 if erros and len(erros) == total else 0


if __name__ == "__main__":
    sys.exit(main())
