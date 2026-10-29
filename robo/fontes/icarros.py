"""iCarros: lê os dados estruturados (JSON-LD) e, se faltarem, os cards da página."""
from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .. import http
from ..modelo import UFS, Anuncio, Busca, numero, slug

BASE = "https://www.icarros.com.br"


def montar_url(busca: Busca, pagina: int) -> str:
    partes = ["comprar"]
    if busca.uf:
        partes.append(slug(UFS[busca.uf]))
    if busca.marca:
        partes.append(slug(busca.marca))
        if busca.modelo:
            partes.append(slug(busca.modelo))
    params = {}
    if not busca.marca:
        params["q"] = busca.texto_busca
    if pagina > 1:
        params["pag"] = pagina
    url = f"{BASE}/{'/'.join(partes)}"
    return url + ("?" + urlencode(params) if params else "")


def _id_da_url(url: str) -> str:
    m = re.search(r"/(?:d|anuncio)?(\d{6,})", url)
    return m.group(1) if m else url


def _do_jsonld(soup: BeautifulSoup) -> list[Anuncio]:
    anuncios = []

    def visitar(no):
        if isinstance(no, list):
            for x in no:
                visitar(x)
        elif isinstance(no, dict):
            tipo = no.get("@type")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if any(t in ("Car", "Vehicle", "Product") for t in tipos) and no.get("url"):
                ofertas = no.get("offers") or {}
                if isinstance(ofertas, list):
                    ofertas = ofertas[0] if ofertas else {}
                km = no.get("mileageFromOdometer")
                url = urljoin(BASE, no["url"])
                anuncios.append(Anuncio(
                    fonte="icarros",
                    id=_id_da_url(url),
                    titulo=no.get("name", ""),
                    url=url,
                    preco=numero(ofertas.get("price")),
                    ano=numero(no.get("vehicleModelDate") or no.get("modelDate") or no.get("productionDate")),
                    km=numero(km.get("value") if isinstance(km, dict) else km),
                ))
            for v in no.values():
                if isinstance(v, (dict, list)):
                    visitar(v)

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            visitar(json.loads(tag.string or ""))
        except json.JSONDecodeError:
            continue
    return anuncios


def _dos_cards(soup: BeautifulSoup) -> list[Anuncio]:
    anuncios, vistos = [], set()
    for a in soup.select('a[href*="/comprar/"]'):
        url = urljoin(BASE, a["href"].split("?")[0])
        if not re.search(r"\d{6,}", url) or url in vistos:
            continue
        vistos.add(url)
        card = a.find_parent(["li", "article", "div"]) or a
        texto = card.get_text(" ", strip=True)
        preco = re.search(r"R\$\s*([\d.]+)", texto)
        ano = re.search(r"\b(19[89]\d|20[0-4]\d)\b", texto)
        km = re.search(r"([\d.]+)\s*km", texto, re.I)
        anuncios.append(Anuncio(
            fonte="icarros",
            id=_id_da_url(url),
            titulo=(a.get("title") or a.get_text(" ", strip=True) or texto[:80]),
            url=url,
            preco=numero(preco.group(1)) if preco else None,
            ano=int(ano.group(1)) if ano else None,
            km=numero(km.group(1)) if km else None,
        ))
    return anuncios


def extrair(html: str) -> list[Anuncio]:
    soup = BeautifulSoup(html, "html.parser")
    return _do_jsonld(soup) or _dos_cards(soup)


def buscar(busca: Busca, max_paginas: int) -> list[Anuncio]:
    resultado = []
    for pagina in range(1, max_paginas + 1):
        anuncios = extrair(http.get(montar_url(busca, pagina)).text)
        # a URL de busca já filtra por UF; o card nem sempre traz o estado
        for a in anuncios:
            a.uf = a.uf or busca.uf
        resultado += anuncios
        if not anuncios:
            break
    return resultado
