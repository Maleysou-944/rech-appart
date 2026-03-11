import pytest

def test_index_retourne_200(client):
    resp = client.get("/")
    assert resp.status_code == 200

def test_index_avec_filtre_ville(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://pap.fr/1", titre="T2", prix=800, ville="Créteil", source="pap"))
    db_session.commit()
    resp = client.get("/?ville=Créteil")
    assert resp.status_code == 200
