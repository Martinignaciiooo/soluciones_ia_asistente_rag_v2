import json
import zipfile

from scripts.exportar_evidencias import exportar_evidencias, guardar_ejecucion, guardar_json


def test_preserva_ensayos_y_errores_sin_inventar_aprobacion(tmp_path):
    primero = guardar_ejecucion(tmp_path, {'traza': {'llamadas': 3, 'citas_validas': True}}, '2026-04-06')
    segundo = guardar_ejecucion(tmp_path, {'traza': {'error': 'NotFoundError', 'llamadas': 0}}, '2026-04-11')
    assert primero != segundo and primero.exists() and segundo.exists()
    assert json.loads(segundo.read_text())['estado_observado'] == 'error'
    with zipfile.ZipFile(exportar_evidencias(tmp_path)) as archivo:
        estado = json.loads(archivo.read('estado_evidencias.json'))
        assert estado['ejecuciones_guardadas'] == 2
        assert not estado['verificacion_base_disponible']


def test_exportacion_omite_secretos_rutas_ajenas_y_enlaces(tmp_path):
    (tmp_path/'.env').write_text('OPENROUTER_API_KEY=clave-privada')
    guardar_json(tmp_path/'docs/evidencias/no_autorizado.json', {'dato': 'no exportar'})
    fuera = tmp_path/'privado.txt'
    fuera.write_text('archivo ajeno')
    (tmp_path/'docs/evidencias/salida_pruebas_colab.txt').symlink_to(fuera)
    guardar_ejecucion(tmp_path, {'OPENROUTER_API_KEY': 'clave-privada',
        'traza': {'mensaje': 'postgresql://persona:secreto@host/base?sslmode=require sk-or-v1-abcdefghijklmnop'}}, '2026-04-06')
    with zipfile.ZipFile(exportar_evidencias(tmp_path)) as archivo:
        nombres = archivo.namelist()
        contenido = '\n'.join(archivo.read(n).decode() for n in nombres)
        assert all('.env' not in n and 'no_autorizado' not in n for n in nombres)
        assert 'salida_pruebas_colab.txt' not in ' '.join(nombres)
        assert 'clave-privada' not in contenido and 'persona:secreto' not in contenido
        assert 'abcdefghijklmnop' not in contenido and 'archivo ajeno' not in contenido
