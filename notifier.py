import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from models import Annonce

def send_email_alert(annonces: List[Annonce], destinataire: str,
                     gmail_user: str, gmail_password: str) -> None:
    if not annonces:
        return

    sujet = f"🏠 {len(annonces)} nouvelle(s) annonce(s) T2 IDF"
    corps = _build_email_body(annonces)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = gmail_user
    msg["To"] = destinataire
    msg.attach(MIMEText(corps, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, destinataire, msg.as_string())


def _build_email_body(annonces: List[Annonce]) -> str:
    lignes = []
    for a in annonces:
        lignes.append(f"""
        <div style="border:1px solid #ddd;padding:12px;margin:8px 0;border-radius:6px">
            <strong><a href="{a.url}">{a.titre}</a></strong><br>
            💶 {a.prix}€ CC &nbsp;|&nbsp;
            📐 {a.surface or "?"}m² &nbsp;|&nbsp;
            📍 {a.ville or "IDF"} &nbsp;|&nbsp;
            🔗 {a.source}
        </div>
        """)
    return f"""
    <html><body>
    <h2>🏠 Nouvelles annonces T2 Île-de-France</h2>
    {''.join(lignes)}
    <p style="color:#666;font-size:12px">AppartSearch IDF</p>
    </body></html>
    """
