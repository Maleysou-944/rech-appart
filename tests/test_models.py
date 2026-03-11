from models import Annonce
from datetime import datetime
import pytest
from sqlalchemy.exc import IntegrityError

def test_annonce_creation(db_session):
    annonce = Annonce(
        url="https://pap.fr/annonce/123",
        titre="T2 Créteil 42m²",
        prix=850,
        surface=42,
        ville="Créteil",
        departement="94",
        source="pap",
    )
    db_session.add(annonce)
    db_session.commit()
    found = db_session.get(Annonce, annonce.id)
    assert found.titre == "T2 Créteil 42m²"
    assert found.prix == 850

def test_annonce_url_unique(db_session):
    url = "https://pap.fr/annonce/456"
    db_session.add(Annonce(url=url, titre="A", prix=800, source="pap"))
    db_session.commit()
    db_session.add(Annonce(url=url, titre="B", prix=800, source="pap"))
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_annonce_est_nouvelle(db_session):
    annonce = Annonce(url="https://pap.fr/1", titre="T", prix=800, source="pap")
    assert annonce.est_nouvelle is True
