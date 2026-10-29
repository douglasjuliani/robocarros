"""Envio de mensagens pelo WhatsApp usando o CallMeBot (gratuito, envia para o seu próprio número).

Ativação (uma vez só): adicione +34 694 29 84 96 aos contatos, mande para ele
"I allow callmebot to send me messages" e guarde a apikey que ele responder.
"""
from __future__ import annotations

import os
import time
from urllib.parse import urlencode

from curl_cffi import requests

from .modelo import Anuncio

API = "https://api.callmebot.com/whatsapp.php"


def formatar(a: Anuncio, busca: str) -> str:
    detalhes = []
    if a.preco:
        detalhes.append(f"R$ {a.preco:,.0f}".replace(",", "."))
    if a.ano:
        detalhes.append(str(a.ano))
    if a.km is not None:
        detalhes.append(f"{a.km:,} km".replace(",", "."))
    local = "/".join(x for x in (a.cidade, a.uf) if x)
    if local:
        detalhes.append(local)
    return f"🚗 *{a.titulo}*\n{' · '.join(detalhes)}\n[{busca} · {a.fonte}]\n{a.url}"


def enviar(texto: str, simular: bool = False) -> None:
    if simular:
        print("---- WhatsApp (simulado) ----\n" + texto + "\n")
        return
    telefone = os.environ["WHATSAPP_TELEFONE"]
    apikey = os.environ["CALLMEBOT_APIKEY"]
    url = f"{API}?{urlencode({'phone': telefone, 'text': texto, 'apikey': apikey})}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    time.sleep(3)  # o CallMeBot limita a frequência de mensagens
