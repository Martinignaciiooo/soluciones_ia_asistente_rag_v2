"""Pruebas de ingesta: parseo de metadatos y preservacion de trazabilidad."""
from pathlib import Path

from src.ingest import cargar_corpus, cargar_documento, detectar_seccion, parsear_frontmatter

BASE = Path(__file__).resolve().parent.parent / "data" / "interna"


def test_frontmatter_se_parsea_completo():
    meta, cuerpo = parsear_frontmatter((BASE / "reglamento_academico.md").read_text(encoding="utf-8"))
    assert meta["doc_id"] == "REG-ACAD-2026"
    assert meta["version"] == "4.2"
    assert meta["vigencia_desde"] == "2026-03-02"
    assert not cuerpo.startswith("---")


def test_todo_fragmento_conserva_metadatos_de_trazabilidad():
    for frag in cargar_corpus(BASE):
        for clave in ("doc_id", "version", "seccion", "chunk_id", "origen"):
            assert clave in frag.metadatos, f"falta {clave} en {frag.metadatos.get('chunk_id')}"
        assert frag.metadatos["origen"] == "interno"


def test_cita_tiene_formato_esperado():
    frag = cargar_corpus(BASE)[0]
    assert frag.cita.startswith("[") and frag.cita.endswith("]")
    assert frag.cita.count(",") == 2


def test_chunk_ids_son_unicos():
    ids = [f.metadatos["chunk_id"] for f in cargar_corpus(BASE)]
    assert len(ids) == len(set(ids))


def test_deteccion_de_seccion_prioriza_encabezado_mas_especifico():
    assert detectar_seccion("### Artículo 42. Retiro\ntexto") == "Artículo 42. Retiro"
    assert detectar_seccion("texto suelto sin encabezado", "Título V") == "Título V"


def test_chunking_respeta_tamano_configurado():
    for frag in cargar_documento(BASE / "reglamento_academico.md", chunk_size=700, chunk_overlap=120):
        assert len(frag.texto) <= 900  # 700 + margen del divisor recursivo
