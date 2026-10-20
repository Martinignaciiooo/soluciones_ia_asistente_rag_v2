"""Memoria duradera de artefactos: recupera borradores, nunca mensajes eliminados."""
from .guardrails import anonimizar


def buscar_borradores(encoder, borradores, consulta, k=2):
    if not borradores:
        return []
    # Entradas acotadas para no indexar un archivo ilimitado en cada consulta.
    documentos = [(ident, anonimizar(titulo)[0][:120], anonimizar(cuerpo)[0][:1600])
                  for ident, titulo, cuerpo in borradores[:20]]
    textos = [titulo+'\n'+cuerpo for _, titulo, cuerpo in documentos]
    vectores = encoder.encode([anonimizar(consulta)[0][:500]]+textos)
    consulta_vector = vectores[0]
    resultados = []
    for (ident, titulo, cuerpo), vector in zip(documentos, vectores[1:]):
        puntaje = sum(a*b for a, b in zip(consulta_vector, vector))
        if puntaje >= 0.38:
            resultados.append({'id': ident, 'titulo': titulo, 'texto': cuerpo,
                'puntaje': puntaje, 'cita': f'[BORRADOR-{ident}, Memoria de la conversación, v1]',
                'fuente_es_normativa': False})
    return sorted(resultados, key=lambda d: d['puntaje'], reverse=True)[:k]
