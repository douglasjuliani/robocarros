"""Mercado Livre: API oficial de busca, categoria Carros e Caminhonetes (MLB1744).

A API exige token de acesso (segredo ML_ACCESS_TOKEN, de um app criado em
https://developers.mercadolivre.com.br). Sem token, lê a página de resultados do site.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .. import http
from ..modelo import UFS, Anuncio, Busca, numero, slug, uf_de

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


LISTA = "https://lista.mercadolivre.com.br/veiculos/carros-caminhonetes"
POR_PAGINA_SITE = 48


def montar_url_site(busca: Busca, pagina: int) -> str:
    partes = [LISTA]
    if busca.marca:
        partes.append(slug(busca.marca))
        if busca.modelo:
            partes.append(slug(busca.modelo))
    if busca.uf:
        partes.append(slug(UFS[busca.uf]))
    caminho = "/".join(partes)
    if not busca.marca:
        caminho += "/" + slug(busca.texto_busca)
    filtros = ""
    if busca.preco_min or busca.preco_max:
        filtros += f"_PriceRange_{busca.preco_min or 0}-{busca.preco_max or 0}"
    if pagina > 1:
        filtros += f"_Desde_{(pagina - 1) * POR_PAGINA_SITE + 1}"
    return caminho + "/" + filtros.lstrip("_") if filtros else caminho + "/"


def extrair_site(html: str) -> list[Anuncio]:
    soup = BeautifulSoup(html, "html.parser")
    anuncios = []
    for card in soup.select(".poly-card, .ui-search-result__wrapper"):
        link = card.select_one("a.poly-component__title, a.ui-search-link, h2 a, h3 a")
        if not link or not link.get("href"):
            continue
        url = link["href"].split("#")[0].split("?")[0]
        id_ = re.search(r"MLB-?(\d+)", url)
        preco = card.select_one(".andes-money-amount__fraction")
        attrs = [li.get_text(" ", strip=True) for li in card.select(".poly-attributes_list__item, .poly-attributes-list__item, .ui-search-card-attributes__attribute")]
        ano = next((numero(t) for t in attrs if re.fullmatch(r"(19|20)\d\d", t)), None)
        km = next((numero(t) for t in attrs if "km" in t.lower()), None)
        local = card.select_one(".poly-component__location, .ui-search-item__location")
        local = local.get_text(" ", strip=True) if local else ""
        partes = [x.strip() for x in re.split(r"[-,]", local) if x.strip()]
        anuncios.append(Anuncio(
            fonte="mercadolivre",
            id=f"MLB{id_.group(1)}" if id_ else url,
            titulo=link.get_text(" ", strip=True),
            url=url,
            preco=numero(preco.get_text()) if preco else None,
            ano=ano,
            km=km,
            cidade=partes[0] if partes else None,
            uf=uf_de(partes[-1]) if partes else None,
        ))
    return anuncios


def buscar(busca: Busca, max_paginas: int) -> list[Anuncio]:
    headers = {}
    if token := os.environ.get("ML_ACCESS_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    else:
        return _buscar_site(busca, max_paginas)
    resultado = []
    for pagina in range(1, max_paginas + 1):
        anuncios = extrair(http.get(montar_url(busca, pagina), headers=headers).json())
        resultado += anuncios
        if len(anuncios) < POR_PAGINA:
            break
    return resultado


def _buscar_site(busca: Busca, max_paginas: int) -> list[Anuncio]:
    resultado = []
    for pagina in range(1, max_paginas + 1):
        html = http.get(montar_url_site(busca, pagina)).text
        anuncios = extrair_site(html)
        if pagina == 1 and not anuncios:
            raise ValueError("Mercado Livre: nenhum anúncio na página (layout mudou ou acesso bloqueado)")
        resultado += anuncios
        if len(anuncios) < POR_PAGINA_SITE:
            break
    return resultado
