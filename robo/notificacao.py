"""Envio dos anúncios novos por e-mail (SMTP). Funciona com Gmail, Outlook e outros.

Variáveis de ambiente:
    SMTP_USUARIO   conta que envia, ex.: seuemail@gmail.com
    SMTP_SENHA     no Gmail, uma "senha de app" (não a senha normal)
    EMAIL_PARA     quem recebe (pode ser o mesmo endereço; vários separados por vírgula)
    SMTP_SERVIDOR  padrão smtp.gmail.com
    SMTP_PORTA     padrão 465 (SSL)
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from html import escape

from .modelo import Anuncio


def _preco(a: Anuncio) -> str:
    return f"R$ {a.preco:,.0f}".replace(",", ".") if a.preco else "—"


def _km(a: Anuncio) -> str:
    return f"{a.km:,} km".replace(",", ".") if a.km is not None else "—"


def _local(a: Anuncio) -> str:
    return "/".join(x for x in (a.cidade, a.uf) if x) or "—"


def montar(novos: list[tuple[str, Anuncio]], lista: list[dict], primeira_vez: bool, limite: int) -> tuple[str, str, str]:
    """Devolve (assunto, texto, html). O corpo é a lista de prioridade, com os novos marcados."""
    n = len(novos)
    if primeira_vez:
        assunto = f"🚗 Robô de carros ativado: {len(lista)} anúncio(s) encontrados"
        intro = ("O robô está funcionando! Abaixo, todos os anúncios encontrados hoje, do mais barato em relação "
                 "à média para o mais caro. A partir de agora você recebe e-mail quando aparecer anúncio novo.")
    else:
        assunto = f"🚗 {n} carro(s) novo(s) encontrado(s)"
        intro = (f"{n} anúncio(s) novo(s) (marcados com 🆕). Lista de prioridade atualizada, "
                 "do mais barato em relação à média para o mais caro:")

    linhas_txt, linhas_html = [], []
    for it in lista[:limite]:
        a = it["anuncio"]
        selo = ("🆕 " if it["novo"] and not primeira_vez else "") + ("⚠️ " if it["suspeito"] else "")
        dif = f"{it['diferenca']:+.1%}"
        linhas_txt.append(f"{it['posicao']}. {selo}{a.titulo} | {_preco(a)} ({dif} vs média R$ {it['media']:,.0f}) | "
                          f"{a.ano or '—'} | {_km(a)} | {_local(a)} | {a.fonte}\n{a.url}".replace(",", "."))
        cor = "#0a7d2c" if it["diferenca"] < 0 else "#b3261e"
        fundo = " style='background:#fff8d6'" if it["novo"] and not primeira_vez else ""
        linhas_html.append(
            f"<tr{fundo}>"
            f"<td>{it['posicao']}</td>"
            f'<td>{selo}<a href="{escape(a.url)}">{escape(a.titulo)}</a></td>'
            f"<td style='white-space:nowrap'><b>{_preco(a)}</b></td>"
            f"<td style='white-space:nowrap;color:{cor}'><b>{dif}</b><br><small>média R$ {it['media']:,.0f}</small></td>".replace(",", ".")
            + f"<td>{a.ano or '—'}</td>"
            f"<td style='white-space:nowrap'>{_km(a)}</td>"
            f"<td>{escape(_local(a))}</td>"
            f"<td>{a.fonte}</td>"
            "</tr>"
        )
    resto = f"…e mais {len(lista) - limite} anúncio(s) na lista completa (RANKING.md no GitHub)." if len(lista) > limite else ""
    legenda = "🆕 = anúncio novo · ⚠️ = mais de 30% abaixo da média: desconfie (golpe, leilão, sinistro)."

    texto = "\n\n".join([intro, *linhas_txt, resto, legenda]).strip()
    cab = "".join(f"<th style='text-align:left;padding:6px'>{c}</th>"
                  for c in ("#", "Anúncio", "Preço", "vs. média", "Ano", "Km", "Local", "Site"))
    html = (
        f"<p>{escape(intro)}</p>"
        "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;font-family:sans-serif;font-size:14px'>"
        f"<tr style='background:#eee'>{cab}</tr>{''.join(linhas_html)}</table>"
        f"<p>{escape(resto)}</p><p><small>{escape(legenda)}</small></p>"
    )
    return assunto, texto, html


def enviar(assunto: str, texto: str, html: str, simular: bool = False) -> None:
    if simular:
        print(f"---- E-mail (simulado) ----\nAssunto: {assunto}\n\n{texto}\n")
        return
    usuario = os.environ["SMTP_USUARIO"]
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"Robô de carros <{usuario}>"
    msg["To"] = os.environ.get("EMAIL_PARA") or usuario
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    servidor = os.environ.get("SMTP_SERVIDOR") or "smtp.gmail.com"
    porta = int(os.environ.get("SMTP_PORTA") or 465)
    if porta == 465:
        with smtplib.SMTP_SSL(servidor, porta, timeout=30) as smtp:
            smtp.login(usuario, os.environ["SMTP_SENHA"])
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(servidor, porta, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(usuario, os.environ["SMTP_SENHA"])
            smtp.send_message(msg)
