"""OLX: lê o JSON embutido na página de resultados (__NEXT_DATA__)."""
from __future__ import annotations

import json
import re
from urllib.parse import urlencode

from .. import http
from ..modelo import Anuncio, Busca, numero, uf_de

BASE = "https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios"


def montar_url(busca: Busca, pagina: int) -> str:
    caminho = BASE + (f"/estado-{busca.uf.lower()}" if busca.uf else "")
    params = {"q": busca.texto_busca, "sf": 1}  # sf=1: mais recentes primeiro
    if busca.preco_min:
        params["ps"] = busca.preco_min
    if busca.preco_max:
        params["pe"] = busca.preco_max
    if pagina > 1:
        params["o"] = pagina
    return f"{caminho}?{urlencode(params)}"


def extrair(html: str) -> list[Anuncio]:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("OLX: __NEXT_DATA__ não encontrado (layout mudou ou acesso bloqueado)")
    dados = json.loads(m.group(1))
    ads = dados.get("props", {}).get("pageProps", {}).get("ads", [])
    anuncios = []
    for ad in ads:
        if not ad.get("subject") or not ad.get("url"):
            continue  # espaços de publicidade
        props = {p.get("name"): p.get("value") for p in ad.get("properties") or []}
        local = ad.get("locationDetails") or {}
        anuncios.append(Anuncio(
            fonte="olx",
            id=str(ad.get("listId") or ad["url"]),
            titulo=ad["subject"],
            url=ad["url"],
            preco=numero(ad.get("price")),
            ano=numero(props.get("regdate")),
            km=numero(props.get("mileage")),
            cidade=local.get("municipality"),
            uf=uf_de(local.get("uf")),
        ))
    return anuncios


def buscar(busca: Busca, max_paginas: int) -> list[Anuncio]:
    resultado = []
    for pagina in range(1, max_paginas + 1):
        anuncios = extrair(http.get(montar_url(busca, pagina)).text)
        resultado += anuncios
        if not anuncios:
            break
    return resultado
