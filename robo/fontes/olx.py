"""OLX: lê os cards de anúncio da página de resultados (ou o antigo JSON __NEXT_DATA__)."""
from __future__ import annotations

import json
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

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


def _dos_cards(html: str) -> list[Anuncio] | None:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('a[data-testid="adcard-link"]')
    if not links:
        return None
    anuncios = []
    for link in links:
        url = link.get("href", "")
        titulo = link.get("title") or link.get_text(" ", strip=True)
        card = link.find_parent(class_="olx-adcard__content") or link.parent
        textos = list(card.stripped_strings)
        preco_i = next((i for i, t in enumerate(textos) if t.startswith("R$")), None)
        km_label = next((x["aria-label"] for x in card.select("[aria-label]") if "quilômetros" in x["aria-label"]), None)
        ano = re.search(r"\b(19[89]\d|20[0-4]\d)\s*$", titulo)
        uf = re.match(r"https://([a-z]{2})\.olx\.com\.br/", url)
        id_ = re.search(r"-(\d{6,})$", url)
        # local vem depois do preço no formato "Cidade, Bairro" (pula selos como "Online")
        local = next((t for t in textos[(preco_i or 0) + 1:] if "," in t), None)
        cidade = local.split(",")[0].strip() if local else None
        anuncios.append(Anuncio(
            fonte="olx",
            id=id_.group(1) if id_ else url,
            titulo=titulo,
            url=url,
            preco=numero(textos[preco_i]) if preco_i is not None else None,
            ano=int(ano.group(1)) if ano else None,
            km=numero(km_label),
            cidade=cidade,
            uf=uf_de(uf.group(1)) if uf else None,
        ))
    return anuncios


def extrair(html: str) -> list[Anuncio]:
    cards = _dos_cards(html)
    if cards is not None:
        return cards
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        if "olx-adcard" not in html and "Nenhum anúncio" not in html:
            raise ValueError("OLX: nenhum anúncio na página (layout mudou ou acesso bloqueado)")
        return []
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
            cambio=props.get("gearbox"),
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
