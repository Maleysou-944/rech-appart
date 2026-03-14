from models import Annonce
from datetime import datetime
import pytest
import json
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

def test_get_images_retourne_liste_vide_si_none():
    a = Annonce(url="https://x.fr/1", titre="T", prix=800, source="pap")
    assert a.get_images() == []

def test_get_images_retourne_liste_vide_si_json_invalide():
    a = Annonce(url="https://x.fr/2", titre="T", prix=800, source="pap")
    a.images = "pas du json"
    assert a.get_images() == []

def test_get_images_retourne_liste_urls():
    a = Annonce(url="https://x.fr/3", titre="T", prix=800, source="pap")
    a.images = json.dumps(["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"])
    assert a.get_images() == ["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"]

def test_get_first_image_retourne_none_si_pas_images():
    a = Annonce(url="https://x.fr/4", titre="T", prix=800, source="pap")
    assert a.get_first_image() is None

def test_get_first_image_retourne_premiere_url():
    a = Annonce(url="https://x.fr/5", titre="T", prix=800, source="pap")
    a.images = json.dumps(["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"])
    assert a.get_first_image() == "https://img1.fr/a.jpg"
