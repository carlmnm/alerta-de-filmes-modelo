#!/usr/bin/env python3
"""Alerta de filmes.

Lista = Issues abertas do repositório (título = nome do filme ou ID do IMDb).
Para cada filme, consulta o AIOStreams (o mesmo que o Nuvio usa). Se houver
pelo menos MIN_STREAMS streams bons (sem CAM/TS), manda e-mail, comenta e
fecha a Issue. Issue fechada = já avisado, então não precisa de arquivo de estado.
"""
import json
from html import escape
from email.utils import formataddr
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage

MANIFEST = os.environ["AIOSTREAMS_MANIFEST_URL"].strip()
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_TO = os.environ.get("EMAIL_TO") or GMAIL_USER
REPO = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ["GITHUB_TOKEN"]
MIN_STREAMS = int(os.environ.get("MIN_STREAMS") or "2")

# Versões gravadas no cinema / baixa qualidade
BAD = re.compile(
    r"\b(cam|hdcam|camrip|ts|hdts|telesync|tc|hdtc|telecine|scr|screener|workprint)\b",
    re.I,
)


def http(url, method="GET", data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return json.loads(body) if body else None


def gh(path, method="GET", payload=None):
    return http(
        f"https://api.github.com/repos/{REPO}{path}",
        method,
        json.dumps(payload).encode() if payload is not None else None,
        {
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "alerta-filmes",
        },
    )


def resolve(title):
    """Devolve (imdb_id, nome_bonito). Aceita 'tt1234567' no título; senão busca no Cinemeta.
    Um ano no fim do título (ex.: 'Dune 2024') ajuda a escolher o filme certo."""
    m = re.search(r"tt\d{6,}", title)
    if m:
        return m.group(0), title.strip()
    ano = None
    texto = title.strip()
    ma = re.search(r"\(?\b((?:19|20)\d{2})\b\)?\s*$", texto)
    if ma:
        ano = ma.group(1)
        texto = texto[: ma.start()].strip() or texto
    q = urllib.parse.quote(texto)
    data = http(
        f"https://v3-cinemeta.strem.io/catalog/movie/top/search={q}.json",
        headers={"User-Agent": "alerta-filmes"},
    )
    metas = (data or {}).get("metas") or []
    if not metas:
        return None, title.strip()
    meta = next(
        (x for x in metas if ano and str(x.get("releaseInfo") or "").startswith(ano)),
        metas[0],
    )
    return meta["id"], f'{meta.get("name")} ({meta.get("releaseInfo") or "?"})'


def good_streams(imdb):
    base = MANIFEST.rsplit("/manifest.json", 1)[0]
    data = http(f"{base}/stream/movie/{imdb}.json", timeout=90)
    out = []
    for s in (data or {}).get("streams", []):
        # o AIOStreams às vezes devolve avisos/erros como se fossem streams
        if not (s.get("url") or s.get("infoHash")):
            continue
        texto = " ".join(
            str(x)
            for x in (
                s.get("name"),
                s.get("description"),
                (s.get("behaviorHints") or {}).get("filename"),
            )
            if x
        )
        if BAD.search(texto):
            continue
        out.append(s)
    return out


def send_mail(subject, texto, html=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("O Faroleiro 🏴‍☠️", GMAIL_USER))
    msg["To"] = EMAIL_TO
    msg.set_content(texto)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.send_message(msg)


def main():
    if not MANIFEST.endswith("/manifest.json"):
        sys.exit("AIOSTREAMS_MANIFEST_URL deve terminar em /manifest.json")

    issues = [i for i in gh("/issues?state=open&per_page=100") if "pull_request" not in i]
    print(f"{len(issues)} filme(s) na lista")

    for issue in issues:
        title = issue["title"]
        try:
            imdb, nome = resolve(title)
            if not imdb:
                print(f"- {title}: não encontrei no Cinemeta (use o ID do IMDb no título)")
                continue

            # na primeira vez, diz qual filme entendeu para você conferir (e marca a Issue)
            if "conferido" not in [l["name"] for l in issue.get("labels", [])]:
                n = issue["number"]
                gh(
                    f"/issues/{n}/comments",
                    "POST",
                    {"body": f"Entendi como **{nome}** ({imdb}). Se estiver errado, "
                             f"coloque o ano ou o ID do IMDb no título."},
                )
                gh(f"/issues/{n}/labels", "POST", {"labels": ["conferido"]})

            streams = good_streams(imdb)
            print(f"- {nome} [{imdb}]: {len(streams)} stream(s) bom(ns)")
            if len(streams) < MIN_STREAMS:
                continue

            texto = (
                f"{nome} acabou de cair do caminhão e já se encontra em águas profundas.\n"
                f"Seu filme tem {len(streams)} streams bons no AIOStreams.\n"
                f"O mar está calmo e estamos prontos para zarpar!"
            )
            corpo_html = f"""
            <div style="background:#eaf2f8;padding:24px 12px;font-family:Georgia,'Times New Roman',serif;">
              <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #cfe0ec;">
                <div style="background:#0b3d5c;color:#ffffff;padding:22px 24px;">
                  <div style="font-size:26px;font-weight:bold;margin-top:6px;">🎬 {escape(nome)}</div>
                </div>
                <div style="padding:24px;color:#1d2b36;font-size:18px;line-height:1.6;">
                  <p style="margin:0 0 14px;">Acabou de cair do caminhão e já se encontra em <b>águas profundas</b>.</p>
                  <p style="margin:0 0 14px;">Seu filme tem <b style="color:#0b6e8a;">{len(streams)} streams bons</b> no AIOStreams.</p>
                  <p style="margin:0;">O mar está calmo e estamos prontos para zarpar! 🌊</p>
                </div>
                <div style="padding:0 24px 26px;">
                  <a href="https://www.imdb.com/title/{imdb}/" style="display:inline-block;background:#0b6e8a;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:8px;font-size:16px;font-family:Arial,sans-serif;">Ver no IMDb</a>
                </div>
              </div>
            </div>
            """
            send_mail(f"Ahoy, sailor! 🎬 {nome}", texto, corpo_html)
            n = issue["number"]
            gh(
                f"/issues/{n}/comments",
                "POST",
                {"body": f"Avisado por e-mail: {len(streams)} streams bons para {nome} ({imdb})."},
            )
            gh(f"/issues/{n}", "PATCH", {"state": "closed"})
        except Exception as e:  # um filme com erro não derruba os outros
            print(f"- {title}: erro: {e}")


if __name__ == "__main__":
    main()
