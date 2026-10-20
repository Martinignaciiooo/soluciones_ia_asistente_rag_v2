import pytest
import psycopg
from src.storage import Store,StorageError


def test_sin_database_url_no_crea_base_local(monkeypatch,tmp_path):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(StorageError,match='Falta DATABASE_URL'):
        Store()
    assert not (tmp_path/'runtime').exists()


def test_url_invalida_no_expone_valor(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','psql postgresql://clave-privada-no-imprimir')
    with pytest.raises(StorageError) as caught:
        Store()
    assert 'clave-privada' not in str(caught.value)


def test_error_de_conexion_no_expone_credenciales(monkeypatch):
    def broken(*args,**kwargs):
        raise psycopg.OperationalError('password=clave-privada-no-imprimir')
    monkeypatch.setattr(psycopg,'connect',broken)
    with pytest.raises(StorageError) as caught:
        Store('postgresql://usuario:clave-privada@db.example.org/proyecto?sslmode=require')
    assert 'clave-privada' not in str(caught.value)


def test_no_permite_ssl_desactivado_en_base_remota():
    with pytest.raises(StorageError,match='sslmode=require'):
        Store('postgresql://usuario:clave@db.example.org/proyecto?sslmode=disable')
