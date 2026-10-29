"""Lista de prioridade: ordena os anúncios pelo preço em relação à média.

A média de referência é a dos anúncios do mesmo ano (quando há pelo menos 3);
senão, a média geral da busca. Quanto mais abaixo da média, maior a prioridade.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .modelo import Anuncio

MIN_MESMO_ANO = 3
SUSPEITO = -0.30  # 30% abaixo da média costuma ser golpe, leilão ou sinistro


def calcular(itens: list[tuple[str, Anuncio]], chaves_novas: set[str] = frozenset()) -> list[dict]:
    por_busca: dict[str, list[Anuncio]] = defaultdict(list)
    for busca, a in sorted(itens, key=lambda x: x[1].preco or 0):
        if a.preco:
            por_busca[busca].append(a)

    # o mesmo carro anunciado em mais de um site: fica o mais barato, com os outros sites anotados
    outros_sites: dict[str, list[str]] = defaultdict(list)
    for busca, anuncios in por_busca.items():
        unicos, vistos = [], {}
        for a in anuncios:
            # km "quebrada" (ex.: 31.791) + mesmo ano identificam bem o veículo
            chave = (a.km, a.ano) if a.km and a.km % 1000 else None
            if chave and chave in vistos and vistos[chave].fonte != a.fonte:
                outros_sites[vistos[chave].chave].append(a.fonte)
                continue
            if chave:
                vistos.setdefault(chave, a)
            unicos.append(a)
        por_busca[busca] = unicos

    lista = []
    for busca, anuncios in por_busca.items():
        media_geral = mean(a.preco for a in anuncios)
        por_ano = defaultdict(list)
        for a in anuncios:
            por_ano[a.ano].append(a.preco)
        for a in anuncios:
            precos_ano = por_ano[a.ano] if a.ano else []
            if len(precos_ano) >= MIN_MESMO_ANO:
                ref, base = mean(precos_ano), f"média {a.ano} ({len(precos_ano)} anúncios)"
            else:
                ref, base = media_geral, f"média geral ({len(anuncios)} anúncios)"
            dif = a.preco / ref - 1
            lista.append({
                "busca": busca,
                "anuncio": a,
                "media": round(ref),
                "diferenca": dif,
                "base": base,
                "novo": a.chave in chaves_novas,
                "outros_sites": sorted(set(outros_sites.get(a.chave, []))),
                "suspeito": dif <= SUSPEITO,
            })
    lista.sort(key=lambda x: x["diferenca"])
    for i, item in enumerate(lista, 1):
        item["posicao"] = i
    return lista


def _fmt_preco(v: int) -> str:
    return f"R$ {v:,.0f}".replace(",", ".")


def markdown(lista: list[dict], data: str) -> str:
    linhas = [
        "# 🚗 Lista de prioridade",
        "",
        f"Atualizada em {data} (UTC). Ordenada do anúncio **mais abaixo da média** para o mais caro.",
        "A média é a dos anúncios do mesmo ano (quando há 3 ou mais); senão, a média geral.",
        "",
        "| # | Anúncio | Preço | Média | Diferença | Ano modelo | Km | Local | Site |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for it in lista:
        a = it["anuncio"]
        marca = (" 🆕" if it["novo"] else "") + (" ⚠️" if it["suspeito"] else "")
        km = f"{a.km:,}".replace(",", ".") if a.km is not None else "—"
        local = "/".join(x for x in (a.cidade, a.uf) if x) or "—"
        titulo = a.titulo.replace("|", "/")
        linhas.append(
            f"| {it['posicao']} | [{titulo}]({a.url}){marca} | **{_fmt_preco(a.preco)}** | "
            f"{_fmt_preco(it['media'])} | {it['diferenca']:+.1%} | {a.ano or '—'} | {km} | {local} | {' + '.join([a.fonte, *it['outros_sites']])} |"
        )
    if not lista:
        linhas.append("| | Nenhum anúncio encontrado com os filtros atuais. | | | | | | | |")
    linhas += ["", "🆕 = apareceu nesta execução · ⚠️ = mais de 30% abaixo da média: desconfie (golpe, leilão, sinistro)."]
    return "\n".join(linhas) + "\n"
