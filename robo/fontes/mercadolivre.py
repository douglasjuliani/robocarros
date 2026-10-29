"""Mercado Livre: API oficial de busca, categoria Carros e Caminhonetes (MLB1744).

A API pode exigir um token de acesso. Se necessário, crie um app em
https://developers.mercadolivre.com.br e defina o segredo ML_ACCESS_TOKEN.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

from .. import http
from ..modelo import Anuncio, Busca, numero, uf_de

API = "https://api.mercadolibre.com/sites/MLB/search"
POR_PAGINA = 50


def montar_url(busca: Busca, pagina: int) -> str:
    params = {
        "category": "MLB1744",
        "q": busca.texto_busca,
        "limit": POR_PAGINA,
        "offset": (pagina - 1) * POR_PAGINA,
        "sort": "date_desc",
    }
    if busca.preco_min or busca.preco_max:
        params["price"] = f"{busca.preco_min or '*'}-{busca.preco_max or '*'}"
    return f"{API}?{urlencode(params)}"


def extrair(dados: dict) -> list[Anuncio]:
    anuncios = []
    for item in dados.get("results") or []:
        attrs = {a.get("id"): a.get("value_name") for a in item.get("attributes") or []}
        local = item.get("location") or {}
        anuncios.append(Anuncio(
            fonte="mercadolivre",
            id=item["id"],
            titulo=item.get("title", ""),
            url=item.get("permalink", ""),
            preco=numero(item.get("price")),
            ano=numero(attrs.get("VEHICLE_YEAR")),
            km=numero(attrs.get("KILOMETERS")),
            cidade=(local.get("city") or {}).get("name"),
            uf=uf_de((local.get("state") or {}).get("name")),
            cambio=attrs.get("TRANSMISSION"),
        ))
    return anuncios


def buscar(busca: Busca, max_paginas: int) -> list[Anuncio]:
    headers = {}
    if token := os.environ.get("ML_ACCESS_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    resultado = []
    for pagina in range(1, max_paginas + 1):
        anuncios = extrair(http.get(montar_url(busca, pagina), headers=headers).json())
        resultado += anuncios
        if len(anuncios) < POR_PAGINA:
            break
    return resultado
