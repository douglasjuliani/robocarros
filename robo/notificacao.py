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


def montar(novos: list[tuple[str, Anuncio]], primeira_vez: bool, limite: int) -> tuple[str, str, str]:
    """Devolve (assunto, texto, html)."""
    n = len(novos)
    if primeira_vez:
        assunto = f"🚗 Robô de carros ativado: {n} anúncio(s) encontrados"
        intro = "O robô está funcionando! Estes são os anúncios que já existem hoje. A partir de agora você recebe só os novos."
    else:
        assunto = f"🚗 {n} carro(s) novo(s) encontrado(s)"
        intro = "Novos anúncios que batem com os seus filtros:"

    linhas_txt, linhas_html = [], []
    for busca, a in novos[:limite]:
        linhas_txt.append(f"[{busca}] {a.titulo} | {_preco(a)} | {a.ano or '—'} | {_km(a)} | {_local(a)} | {a.fonte}\n{a.url}")
        linhas_html.append(
            "<tr>"
            f"<td>{escape(busca)}</td>"
            f'<td><a href="{escape(a.url)}">{escape(a.titulo)}</a></td>'
            f"<td style='white-space:nowrap'><b>{_preco(a)}</b></td>"
            f"<td>{a.ano or '—'}</td>"
            f"<td style='white-space:nowrap'>{_km(a)}</td>"
            f"<td>{escape(_local(a))}</td>"
            f"<td>{a.fonte}</td>"
            "</tr>"
        )
    resto = f"…e mais {n - limite} anúncio(s). Refine os filtros no config.yaml." if n > limite else ""

    texto = "\n\n".join([intro, *linhas_txt, resto]).strip()
    cab = "".join(f"<th style='text-align:left;padding:6px'>{c}</th>"
                  for c in ("Busca", "Anúncio", "Preço", "Ano", "Km", "Local", "Site"))
    html = (
        f"<p>{escape(intro)}</p>"
        "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;font-family:sans-serif;font-size:14px'>"
        f"<tr style='background:#eee'>{cab}</tr>{''.join(linhas_html)}</table>"
        f"<p>{escape(resto)}</p>"
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
