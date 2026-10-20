"""Guarda ejecuciones y exporta evidencia existente. No llama a modelos ni a la BD."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4
import zipfile


def sanear(valor):
    """Evita incluir credenciales conocidas; usar siempre consultas sintéticas."""
    if isinstance(valor, dict):
        return {k: ('[SECRETO OMITIDO]' if any(p in k.lower() for p in
                ('api_key', 'database_url', 'password', 'authorization', 'access_token'))
                else sanear(v)) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [sanear(v) for v in valor]
    if isinstance(valor, str):
        valor = re.sub(r'postgres(?:ql)?://[^\s"\'<>]+', '[CONEXIÓN OMITIDA]', valor)
        return re.sub(r'\bsk-(?:or-v1-)?[A-Za-z0-9_-]{12,}', '[CLAVE OMITIDA]', valor)
    return valor


def guardar_json(ruta, contenido):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(sanear(contenido), ensure_ascii=False, indent=2), encoding='utf-8')
    return ruta


def guardar_ejecucion(raiz, resultado, fecha_simulada, origen='Colab'):
    """Conserva cada resultado, incluidos errores, sin sobreescribir ensayos anteriores."""
    ahora = datetime.now(timezone.utc)
    traza = resultado.get('traza', {})
    evidencia = {
        'tipo_evidencia': 'ejecución del agente con proveedor OpenRouter configurado',
        'origen': origen,
        'fecha_ejecucion_utc': ahora.isoformat(),
        'fecha_simulada': str(fecha_simulada),
        'estado_observado': 'error' if traza.get('error') else 'resultado recibido; revisar contenido',
        'llamadas_chat_exitosas': traza.get('llamadas', 0),
        'validacion_citas_reportada': traza.get('citas_validas'),
        'resultado': resultado,
    }
    nombre = ahora.strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:10] + '.json'
    return guardar_json(Path(raiz)/'docs/evidencias/ejecuciones'/nombre, evidencia)


def exportar_evidencias(raiz, destino=None):
    """Sólo empaqueta rutas aprobadas; nunca recorre .env, notebooks ni bases de datos."""
    raiz = Path(raiz).resolve()
    base = raiz/'docs/evidencias'
    ejecuciones = sorted((base/'ejecuciones').glob('*.json'))
    fijas = [base/'prueba_base_datos.json', base/'salida_pruebas_colab.txt',
             raiz/'runtime/corpus_manifest.json']
    destino = Path(destino) if destino else raiz/'runtime/Evidencias_AsistenteReg_EP2.zip'
    destino.parent.mkdir(parents=True, exist_ok=True)
    estado = {
        'fecha_exportacion_utc': datetime.now(timezone.utc).isoformat(),
        'ejecuciones_guardadas': len(ejecuciones),
        'verificacion_base_disponible': fijas[0].is_file(),
        'pruebas_colab_disponibles': fijas[1].is_file(),
        'manifest_manual_disponible': fijas[2].is_file(),
        'aviso': 'La presencia de archivos no demuestra aprobación. Revisar resultados, citas y errores.',
    }
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as archivo:
        for ruta in ejecuciones + fijas:
            if not ruta.is_file() or ruta.is_symlink():
                continue
            contenido = ruta.read_text(encoding='utf-8')
            if ruta.suffix == '.json':
                contenido = json.dumps(sanear(json.loads(contenido)), ensure_ascii=False, indent=2)
            else:
                contenido = sanear(contenido)
            nombre = 'docs/evidencias/corpus_manifest.json' if ruta == fijas[2] else ruta.relative_to(raiz).as_posix()
            archivo.writestr(nombre, contenido)
        archivo.writestr('estado_evidencias.json', json.dumps(estado, ensure_ascii=False, indent=2))
        archivo.writestr('LEEME.txt',
            'Evidencia exportada desde el entorno del equipo. No se ejecutaron llamadas al exportar.\n'
            'Los JSON de ejecuciones conservan también errores. Revisar la traza de cada consulta.\n'
            'prueba_base_datos.json corresponde a PostgreSQL sin IA; los tests simulan la API.\n'
            'Usar sólo datos sintéticos y revisar los archivos antes de publicarlos.\n'
            'Copiar docs/evidencias a la raiz del proyecto y subir los archivos al repositorio v2.\n')
    return destino


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path)
    args = parser.parse_args()
    print(exportar_evidencias(Path(__file__).resolve().parents[1], args.destino))
