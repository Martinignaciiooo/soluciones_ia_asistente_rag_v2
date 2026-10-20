"""Ranking BM25 y fusión RRF. No ejecuta modelos de IA."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .ingest import Fragmento

TOKEN = re.compile(r"[a-záéíóúñü0-9\-]+", re.IGNORECASE)

STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "se", "que", "por",
    "un", "una", "para", "con", "no", "su", "al", "es", "o", "lo", "como",
    "mas", "pero", "sus", "le", "ya", "cuando", "todo", "esta", "ser", "son",
    "puedo", "quiero", "hola", "gracias", "me", "mi", "si", "hay",
}


def tokenizar(texto: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(texto) if t.lower() not in STOPWORDS]


@dataclass
class Resultado:
    fragmento: Fragmento
    puntaje: float
    fuente: str  # "lexico" | "vectorial" | "externo"


class RecuperadorLexico:
    def __init__(self, fragmentos: list[Fragmento], k1: float = 1.5, b: float = 0.75):
        self.fragmentos = fragmentos
        self.k1, self.b = k1, b
        self.docs = [tokenizar(f.texto) for f in fragmentos]
        self.largos = [len(d) for d in self.docs]
        self.largo_medio = sum(self.largos) / len(self.docs) if self.docs else 0.0
        self.frecuencias = [Counter(d) for d in self.docs]
        self.df: Counter = Counter()
        for d in self.docs:
            self.df.update(set(d))
        self.n = len(self.docs)

    def _idf(self, termino: str) -> float:
        df = self.df.get(termino, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def buscar(self, consulta: str, k: int = 4) -> list[Resultado]:
        terminos = tokenizar(consulta)
        puntajes: list[tuple[int, float]] = []
        for i, tf in enumerate(self.frecuencias):
            s = 0.0
            for t in terminos:
                if t not in tf:
                    continue
                num = tf[t] * (self.k1 + 1)
                den = tf[t] + self.k1 * (1 - self.b + self.b * self.largos[i] / (self.largo_medio or 1))
                s += self._idf(t) * num / den
            if s > 0:
                puntajes.append((i, s))
        puntajes.sort(key=lambda x: x[1], reverse=True)
        maximo = puntajes[0][1] if puntajes else 1.0
        return [
            Resultado(self.fragmentos[i], round(s / maximo, 4), "lexico")
            for i, s in puntajes[:k]
        ]


def fusionar_rrf(listas: list[list[Resultado]], k: int = 4, constante: int = 60) -> list[Resultado]:
    # RRF: sum(1 / (constante + rango))
    acumulado: dict[str, float] = {}
    referencia: dict[str, Resultado] = {}
    for lista in listas:
        for rango, res in enumerate(lista, start=1):
            clave = res.fragmento.metadatos.get("chunk_id", res.fragmento.texto[:60])
            acumulado[clave] = acumulado.get(clave, 0.0) + 1.0 / (constante + rango)
            if clave not in referencia or res.puntaje > referencia[clave].puntaje:
                referencia[clave] = res
    ordenado = sorted(acumulado.items(), key=lambda x: x[1], reverse=True)[:k]
    fusionados = []
    for clave, puntaje_rrf in ordenado:
        base = referencia[clave]
        fusionados.append(Resultado(base.fragmento, base.puntaje, base.fuente))
    return fusionados
