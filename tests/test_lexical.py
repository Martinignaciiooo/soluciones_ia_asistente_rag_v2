"""Pruebas de la capa de recuperacion (BM25 y fusion RRF), sin API externa."""
import json
from pathlib import Path

import pytest

from src.ingest import cargar_corpus
from src.lexical import RecuperadorLexico, Resultado, fusionar_rrf, tokenizar

BASE = Path(__file__).resolve().parent.parent / "data" / "interna"
FRAGMENTOS = cargar_corpus(BASE)
RECUPERADOR = RecuperadorLexico(FRAGMENTOS)


def test_tokenizacion_elimina_stopwords():
    assert "de" not in tokenizar("plazo de retiro de la asignatura")
    assert "retiro" in tokenizar("plazo de retiro de la asignatura")


@pytest.mark.parametrize(
    "consulta,doc_esperado",
    [
        ("plazo para retirar una asignatura", "REG-ACAD-2026"),
        ("etapas del proceso de titulación", "PROC-TIT-2026"),
        ("horario de atención presencial", "FAQ-REG-2026"),
        ("fecha de cierre de actas", "CAL-ACAD-2026-01"),
    ],
)
def test_recupera_el_documento_correcto(consulta, doc_esperado):
    docs = [r.fragmento.metadatos["doc_id"] for r in RECUPERADOR.buscar(consulta, k=4)]
    assert doc_esperado in docs


def test_consulta_sin_coincidencias_devuelve_lista_vacia():
    assert RECUPERADOR.buscar("zzzz qqqq xxxx", k=4) == []


def test_puntajes_estan_normalizados_y_ordenados():
    res = RECUPERADOR.buscar("convalidación de asignaturas", k=4)
    assert res[0].puntaje == 1.0
    assert all(0.0 <= r.puntaje <= 1.0 for r in res)
    assert res == sorted(res, key=lambda r: r.puntaje, reverse=True)


def test_rrf_deduplica_y_prioriza_consenso():
    a, b, c = FRAGMENTOS[0], FRAGMENTOS[1], FRAGMENTOS[2]
    lista1 = [Resultado(a, 0.9, "lexico"), Resultado(b, 0.5, "lexico")]
    lista2 = [Resultado(c, 0.95, "vectorial"), Resultado(a, 0.4, "vectorial")]
    fusion = fusionar_rrf([lista1, lista2], k=3)
    ids = [r.fragmento.metadatos["chunk_id"] for r in fusion]
    assert len(ids) == len(set(ids))
    assert ids[0] == a.metadatos["chunk_id"]

