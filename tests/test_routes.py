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


def test_filtre_departement(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/1", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/2", titre="T", prix=800, ville="Créteil", departement="94", source="pap"))
    db_session.commit()
    resp = client.get("/?departement=75")
    assert resp.status_code == 200
    assert "Paris".encode() in resp.data
    assert "Créteil".encode() not in resp.data


def test_filtre_source(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/3", titre="T", prix=700, ville="Montreuil", departement="93", source="bienici"))
    db_session.add(Annonce(url="https://x.fr/4", titre="T", prix=700, ville="Vincennes", departement="94", source="pap"))
    db_session.commit()
    resp = client.get("/?source=bienici")
    assert resp.status_code == 200
    assert "Montreuil".encode() in resp.data
    assert "Vincennes".encode() not in resp.data


def test_filtre_multi_departement(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/5", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/6", titre="T", prix=800, ville="Nanterre", departement="92", source="pap"))
    db_session.add(Annonce(url="https://x.fr/7", titre="T", prix=800, ville="Bobigny", departement="93", source="pap"))
    db_session.commit()
    resp = client.get("/?departement=75&departement=92")
    assert "Paris".encode() in resp.data
    assert "Nanterre".encode() in resp.data
    assert "Bobigny".encode() not in resp.data


def test_sans_filtre_retourne_tout(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/8", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/9", titre="T", prix=800, ville="Créteil", departement="94", source="bienici"))
    db_session.commit()
    resp = client.get("/")
    assert "Paris".encode() in resp.data
    assert "Créteil".encode() in resp.data
