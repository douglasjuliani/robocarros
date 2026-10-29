"""Cliente HTTP que imita um navegador Chrome (reduz bloqueios anti-robô)."""
from __future__ import annotations

import random
import time

from curl_cffi import requests

_sessao = None


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
    resp = sessao().get(url, **kwargs)
    resp.raise_for_status()
    return resp
