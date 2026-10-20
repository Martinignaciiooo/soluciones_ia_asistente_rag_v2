"""Prueba real manual: embeddings y chat de OpenRouter consumen saldo del grupo."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from src.provider import OpenRouter,OpenRouterEmbeddings
from src.storage import Store
from src.retrieval import Retrieval
from src.agent import Agent
from scripts.exportar_evidencias import guardar_ejecucion
store=Store()
provider=OpenRouter(store)
retrieval=Retrieval(OpenRouterEmbeddings(provider),cache_dir=ROOT/'runtime')
agent=Agent(store,retrieval,provider,today='2026-04-06')
result=agent.respond('¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta con los requisitos.','smoke-real','smoke-real')
result.update(fecha_ejecucion_utc=datetime.now(timezone.utc).isoformat(),tipo_evidencia='OpenRouter real: embeddings y chat')
out=ROOT/'docs/evidencias/prueba_real_openrouter.json';out.parent.mkdir(parents=True,exist_ok=True)
from scripts.exportar_evidencias import guardar_json
guardar_json(out, result)
guardar_ejecucion(ROOT, result, '2026-04-06', origen='script manual')
print(result['respuesta']);print('Llamadas de chat:',result['traza']['llamadas'],'Costo/reservas acumulados:',store.spent())
print('Evidencia guardada en',out)
if not result['traza'].get('citas_validas') or not result['borradores']:raise SystemExit('Prueba incompleta. Revisa la traza antes de presentar.')
