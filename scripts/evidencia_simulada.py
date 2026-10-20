"""Evidencia de contratos con SDK simulado. No es inferencia real ni usa claves."""
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.test_agent import Scripted,LexicalRetrieval,call,draft_step,final_draft
from src.agent import Agent
from src.storage import Store
results=[]
with tempfile.TemporaryDirectory() as folder:
    store=Store(Path(folder)/'db.sqlite3')
    for day in ['2026-04-06','2026-04-11']:
        provider=Scripted([call('buscar_normativa',consulta='retiro de asignaturas'),call('evaluar_plazo',tramite='retiro'),draft_step,final_draft])
        result=Agent(store,LexicalRetrieval(),provider,today=day).respond('Prepara un borrador de consulta sobre retiro de asignaturas',session=day)
        result.update(tipo_evidencia='API simulada, sin inferencia real de chat ni embeddings',fecha_simulada=day)
        assert result['traza']['citas_validas'] and len(result['borradores'])==1
        results.append(result)
out=ROOT/'docs/evidencias/flujos_simulados.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('Dos flujos verificados con SDK simulado. No hubo solicitudes pagadas.')
