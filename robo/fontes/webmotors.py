"""Webmotors: usa a API JSON que o próprio site chama na página de estoque."""
from __future__ import annotations

from urllib.parse import quote, urlencode

from .. import http
from ..modelo import UFS, Anuncio, Busca, numero, slug, uf_de

API = "https://www.webmotors.com.br/api/search/car"


def montar_url(busca: Busca, pagina: int) -> str:
    caminho = "carros/estoque"
    if busca.marca:
        caminho += f"/{slug(busca.marca)}"
        if busca.modelo:
            caminho += f"/{slug(busca.modelo)}"
    filtros = {}
    if busca.uf:
        filtros["estadocidade"] = UFS[busca.uf]
    for param, valor in (("anode", busca.ano_min), ("anoate", busca.ano_max), ("kmate", busca.km_max),
                         ("precode", busca.preco_min), ("precoate", busca.preco_max)):
        if valor:
            filtros[param] = valor
    if not busca.marca and busca.texto_busca:
        filtros["q"] = busca.texto_busca
    url_site = f"https://www.webmotors.com.br/{caminho}"
    if filtros:
        url_site += "?" + urlencode(filtros)
    params = {
        "url": url_site,
        "actualPage": pagina,
        "displayPerPage": 24,
        "order": 1,
        "showMenu": "false",
        "showCount": "true",
        "showBreadCrumb": "false",
        "testAB": "false",
        "returnUrl": "false",
    }
    return f"{API}?{urlencode(params, quote_via=quote)}"


def _valor(campo):
    return campo.get("Value") if isinstance(campo, dict) else campo


def extrair(dados: dict) -> list[Anuncio]:
    anuncios = []
    for item in dados.get("SearchResults") or []:
        spec = item.get("Specification") or {}
        vendedor = item.get("Seller") or {}
        precos = item.get("Prices") or {}
        marca, modelo, versao = (_valor(spec.get(k)) or "" for k in ("Make", "Model", "Version"))
        ano = numero(spec.get("YearModel")) or numero(spec.get("YearFabrication"))
        uid = item.get("UniqueId")
        url = (
            f"https://www.webmotors.com.br/comprar/{slug(marca)}/{slug(modelo)}/"
            f"{slug(versao)}/{spec.get('NumberPorts') or 4}-portas/{ano or ''}/{uid}"
        )
        anuncios.append(Anuncio(
            fonte="webmotors",
            id=str(uid),
            titulo=spec.get("Title") or f"{marca} {modelo} {versao}".strip(),
            url=url,
            preco=numero(precos.get("Price") or precos.get("SearchPrice")),
            ano=ano,
            km=numero(spec.get("Odometer")),
            cidade=vendedor.get("City"),
            uf=uf_de(vendedor.get("State")),
            cambio=_valor(spec.get("Transmission")),
            ano_fab=numero(spec.get("YearFabrication")),
        ))
    return anuncios


def buscar(busca: Busca, max_paginas: int) -> list[Anuncio]:
    resultado = []
    for pagina in range(1, max_paginas + 1):
        resp = http.get(montar_url(busca, pagina), headers={"Referer": "https://www.webmotors.com.br/"})
        dados = resp.json()
        if pagina == 1 and dados.get("SearchResults"):
            http.salvar_amostra("webmotors", dados["SearchResults"][0])
        anuncios = extrair(dados)
        resultado += anuncios
        if not anuncios:
            break
    return resultado
