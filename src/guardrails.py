"""Guardrails: anonimizacion de datos personales (Ley 19.628), temas fuera de
alcance, abstencion y validacion de citas."""
from __future__ import annotations

import re

# Patrones de datos personales
PATRONES_PII = {
    "RUT": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}\s?[-‐]\s?[\dkK]\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "TELEFONO": re.compile(r"\b(?:\+?56)?\s?9\s?\d{4}\s?\d{4}\b"),
    "MATRICULA": re.compile(r"\bmatr[ií]cula\s+n?[°º]?\s?\d{6,}\b", re.IGNORECASE),
}

# Temas fuera del mandato del asistente
TEMAS_VEDADOS = (
    "demanda", "demandar", "abogado", "juicio", "sumario",
    "suicid", "deprimid", "ansiedad severa", "autolesion",
    "cuanto debo", "mi deuda", "mi saldo", "repactar",
)

DERIVACIONES = {
    "legal": "Direccion de Asuntos Estudiantiles: dae@ejemplo-ip.cl",
    "salud": "Unidad de Apoyo al Estudiante: apoyo@ejemplo-ip.cl, +56 2 2xxx xxxx",
    "financiero": "Oficina de Finanzas Estudiantiles: finanzas@ejemplo-ip.cl",
}


def anonimizar(texto: str) -> tuple[str, dict[str, int]]:
    """Reemplaza datos personales por marcadores y cuenta cuantos hubo."""
    conteo: dict[str, int] = {}
    saneado = texto
    for etiqueta, patron in PATRONES_PII.items():
        saneado, n = patron.subn(f"[{etiqueta}_ANONIMIZADO]", saneado)
        if n:
            conteo[etiqueta] = n
    return saneado, conteo


def fuera_de_alcance(consulta: str) -> str | None:
    texto = consulta.lower()
    if any(t in texto for t in ("suicid", "deprimid", "autolesion", "ansiedad severa")):
        return "salud"
    if any(t in texto for t in ("demanda", "demandar", "abogado", "juicio", "sumario")):
        return "legal"
    if any(t in texto for t in ("cuanto debo", "mi deuda", "mi saldo", "repactar")):
        return "financiero"
    return None
