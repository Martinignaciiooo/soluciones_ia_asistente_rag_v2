"""Carga de documentos internos, metadatos y chunking."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SEPARADORES = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]


@dataclass
class Fragmento:
    texto: str
    metadatos: dict = field(default_factory=dict)

    @property
    def cita(self) -> str:
        m = self.metadatos
        return f"[{m.get('doc_id', 's/d')}, {m.get('seccion', 's/d')}, v{m.get('version', 's/d')}]"


def parsear_frontmatter(contenido: str) -> tuple[dict, str]:
    if not contenido.startswith("---"):
        return {}, contenido
    partes = contenido.split("---", 2)
    if len(partes) < 3:
        return {}, contenido
    meta: dict = {}
    for linea in partes[1].strip().splitlines():
        if ":" in linea:
            clave, _, valor = linea.partition(":")
            meta[clave.strip()] = valor.strip()
    return meta, partes[2].strip()


def detectar_seccion(texto: str, seccion_previa: str = "General") -> str:
    for patron in (r"^###\s+(.+)$", r"^##\s+(.+)$", r"^#\s+(.+)$"):
        m = re.search(patron, texto, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    m = re.search(r"(Art[ií]culo\s+\d+)", texto)
    if m:
        return m.group(1)
    return seccion_previa


def dividir_texto(texto: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    # usa langchain si esta instalado, si no un divisor simple por parrafos
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARADORES,
        )
        return splitter.split_text(texto)
    except ImportError:  # pragma: no cover
        trozos, actual = [], ""
        for parrafo in texto.split("\n\n"):
            if len(actual) + len(parrafo) <= chunk_size:
                actual += ("\n\n" if actual else "") + parrafo
            else:
                if actual:
                    trozos.append(actual)
                actual = parrafo
        if actual:
            trozos.append(actual)
        return trozos


def cargar_documento(ruta: Path, chunk_size: int = 700, chunk_overlap: int = 120) -> list[Fragmento]:
    contenido = ruta.read_text(encoding="utf-8")
    meta_doc, cuerpo = parsear_frontmatter(contenido)
    fragmentos: list[Fragmento] = []
    seccion = "General"
    for i, trozo in enumerate(dividir_texto(cuerpo, chunk_size, chunk_overlap)):
        seccion = detectar_seccion(trozo, seccion)
        metadatos = dict(meta_doc)
        metadatos.update(
            {
                "origen": "interno",
                "archivo": ruta.name,
                "seccion": seccion,
                "chunk_id": f"{meta_doc.get('doc_id', ruta.stem)}#{i:03d}",
            }
        )
        fragmentos.append(Fragmento(texto=trozo.strip(), metadatos=metadatos))
    return fragmentos


def cargar_corpus(directorio: Path, chunk_size: int = 700, chunk_overlap: int = 120) -> list[Fragmento]:
    fragmentos: list[Fragmento] = []
    for ruta in sorted(Path(directorio).glob("*.md")):
        fragmentos.extend(cargar_documento(ruta, chunk_size, chunk_overlap))
    return fragmentos
