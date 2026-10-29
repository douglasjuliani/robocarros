"""Cliente HTTP que imita um navegador Chrome (reduz bloqueios anti-robô)."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from curl_cffi import requests

_sessao = None
ultima_resposta = None  # guardada para depurar quando um site falhar
DEBUG = Path(__file__).resolve().parent.parent / "dados" / "debug"


def sessao():
    global _sessao
    if _sessao is None:
        _sessao = requests.Session(impersonate="chrome")
        _sessao.headers.update({"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
    return _sessao


def get(url: str, **kwargs):
    """GET com pausa aleatória (para não sobrecarregar os sites) e erro em status != 2xx."""
    time.sleep(random.uniform(1.0, 2.5))
    kwargs.setdefault("timeout", 30)
    global ultima_resposta
    resp = ultima_resposta = sessao().get(url, **kwargs)
    resp.raise_for_status()
    return resp


def salvar_debug(nome: str) -> None:
    """Salva a última página baixada (útil para ver por que um site falhou)."""
    if ultima_resposta is not None:
        DEBUG.mkdir(parents=True, exist_ok=True)
        (DEBUG / f"{nome}.html").write_text(
            f"<!-- {ultima_resposta.status_code} {ultima_resposta.url} -->\n{ultima_resposta.text[:5_000_000]}")


def salvar_amostra(nome: str, dados) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    (DEBUG / f"{nome}_amostra.json").write_text(json.dumps(dados, indent=1, ensure_ascii=False))
