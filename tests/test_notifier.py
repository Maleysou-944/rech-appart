from unittest.mock import patch, MagicMock
from notifier import send_email_alert
from models import Annonce

def test_send_email_alert_appelle_smtp(app):
    with app.app_context():
        annonces = [
            Annonce(url="https://pap.fr/1", titre="T2 Créteil 42m²", prix=850,
                    surface=42, ville="Créteil", source="pap"),
        ]
        with patch("notifier.smtplib.SMTP_SSL") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            send_email_alert(annonces, destinataire="test@example.com",
                             gmail_user="user@gmail.com", gmail_password="pass")
            assert mock_server.login.called
            assert mock_server.sendmail.called

def test_send_email_alert_ne_fait_rien_si_liste_vide(app):
    with app.app_context():
        with patch("notifier.smtplib.SMTP_SSL") as mock_smtp:
            send_email_alert([], "test@test.com", "u", "p")
            assert not mock_smtp.called
