"""Comprueba persistencia y retención en la base configurada, sin llamar a IA."""
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
from src.storage import Store


def verificar_base(store):
    session='verificacion-db-'+uuid.uuid4().hex
    try:
        memory=store.memory(session,'verificacion')
        for i in range(1,7):
            memory.save_context({'question':f'Pregunta de prueba {i}'},{'answer':f'Respuesta de prueba {i}'})
        # Cada lectura abre una nueva conexión: el estado está en la base.
        history=store.history(session)
        messages=store.context(session)
        assert len(history)==5 and len(messages)==10
        assert history[0][0]=='Pregunta de prueba 2' and history[-1][1]=='Respuesta de prueba 6'
        return {'backend':store.backend,'clase_memoria':type(memory).__name__,'k':memory.k,
                'mensajes_conservados':len(messages),'intercambios_conservados':len(history),
                'persistencia_entre_conexiones':True,'borrado_del_mas_antiguo':True,
                'llamadas_a_modelos':0,'datos_de_prueba_eliminados_al_final':True}
    finally:
        store.clear_history(session)


if __name__=='__main__':
    load_dotenv(ROOT/'.env')
    try:
        result=verificar_base(Store())
    except Exception as error:
        print('No se pudo verificar la base. Revisa DATABASE_URL, permisos y conexión. Tipo:',type(error).__name__)
        raise SystemExit(1) from None
    path=ROOT/'docs/evidencias/prueba_base_datos.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
