"""Reproduce borrador válido + cierre sin citas usando el manual del proyecto."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from src.agent import Agent,ABSTAIN
from src.ingest import cargar_corpus
from src.lexical import Resultado
from src.retrieval import Retrieval
from src.storage import Store
from tests.test_agent import Scripted,call


class ManualRecuperado:
    def __init__(self):
        self.fragments=cargar_corpus(Path(__file__).resolve().parents[1]/'data/interna')
    def search(self,query,k=3):
        starts=('CAL-ACAD-2026-01,','REG-ACAD-2026, Artículo 53.','REG-ACAD-2026, Artículo 42.')
        selected=[next(f for f in self.fragments if f.cita.startswith('['+start)) for start in starts]
        return [Resultado(f,1.,'vectorial') for f in selected[:k]]


def normas_y_plazo():
    return {'role':'assistant','tool_calls':[
        call('buscar_normativa',consulta='retiro de asignatura')['tool_calls'][0],
        call('evaluar_plazo',tramite='retiro')['tool_calls'][0]]}


def guardar_con_citas(messages):
    docs=json.loads(next(m['content'] for m in messages if m['role']=='tool' and 'documentos' in m['content']))['documentos']
    cites=[doc['cita'] for doc in docs if doc['origen']!='reglamento_academico.md' or 'Artículo 42.' in doc['cita']]
    return call('guardar_borrador',titulo='Consulta de retiro',cuerpo='Solicito orientación sobre el retiro. '+' '.join(cites))


def ejecutar(tmp_path,final,today='2026-04-06'):
    store=Store(tmp_path/'db.sqlite3')
    provider=Scripted([normas_y_plazo(),guardar_con_citas,{'role':'assistant','content':final}])
    result=Agent(store,ManualRecuperado(),provider,today=today).respond(
        '¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta con los requisitos.')
    return result,store,provider


@pytest.mark.parametrize('final',['He preparado el borrador solicitado.',''])
def test_borrador_con_evidencia_no_termina_en_falsa_abstencion(tmp_path,final):
    result,store,provider=ejecutar(tmp_path,final)
    assert ABSTAIN not in result['respuesta']
    assert '10-04-2026' in result['respuesta'] and '12 créditos SCT' in result['respuesta']
    assert 'Borrador guardado #1' in result['respuesta'] and len(result['borradores'])==1
    assert result['traza']['citas_validas'] is True
    assert result['traza']['citas_validas_llm'] is False
    assert result['traza']['validacion_final']=='respuesta_desde_evidencia_y_borrador_validado'
    assert result['traza']['llamadas']==3 and len(provider.prompts)==3
    assert store.history('demo')[0][1]==result['respuesta']
    docs=result['traza']['herramientas'][0]['resultado']['documentos']
    assert all(doc['chunk_id'] and doc['metodo']=='vectorial' for doc in docs)


def test_reconstruccion_descarta_afirmacion_y_cita_inventadas(tmp_path):
    result,_,_=ejecutar(tmp_path,'El retiro es gratuito y siempre se aprueba. [REG-ACAD-2026, Artículo 999, v4.2]')
    assert result['traza']['citas_validas']
    assert 'gratuito' not in result['respuesta'] and 'siempre se aprueba' not in result['respuesta']
    assert 'Artículo 999' not in result['respuesta'] and 'Artículo 42.' in result['respuesta']


def test_recuperacion_respeta_plazo_vencido(tmp_path):
    result,_,_=ejecutar(tmp_path,'Borrador listo.',today='2026-04-11')
    assert 'vencido' in result['respuesta'] and '10-04-2026' in result['respuesta']
    assert 'ORIENTACIÓN POR PLAZO VENCIDO' in result['borradores'][0][2]
    assert result['traza']['citas_validas']


def test_recuperacion_declara_calendario_no_aplicable(tmp_path):
    result,_,_=ejecutar(tmp_path,'Borrador listo.',today='2026-10-20')
    assert 'no aplica a la fecha consultada' in result['respuesta']
    assert 'calendario vigente' in result['respuesta'] and 'está vigente' not in result['respuesta']
    assert result['traza']['citas_validas']


def test_borrador_anterior_no_autoriza_reconstruccion(tmp_path):
    store=Store(tmp_path/'db.sqlite3')
    draft=store.draft('demo','anterior','Anterior','Texto con referencia anterior.')
    agent=Agent(store,ManualRecuperado(),Scripted([]))
    state={'draft_id':draft[0],'session':'demo','evidence':{},'trace':{'herramientas':[]}}
    assert agent._answer_from_saved_draft(state) is None


def test_indexacion_usa_archivos_y_fragmentos_del_manual_indicado(tmp_path):
    folder=tmp_path/'manual';folder.mkdir()
    content='---\ndoc_id: MANUAL-GRUPO\nversion: 1\n---\n\n## Norma del grupo\n'+('\n\nLa norma del grupo exige revisar antecedentes antes de formalizar el trámite.'*40)
    document=folder/'manual_grupo.md';document.write_text(content,encoding='utf-8')
    calls=[]
    class Encoder:
        model_id='embeddings-simulados'
        def encode(self,texts):calls.append(list(texts));return [[1.,0.] for text in texts]
    retrieval=Retrieval(Encoder(),folder,tmp_path/'cache')
    assert len(retrieval.fragments)>1 and calls==[[f.texto for f in retrieval.fragments]]
    assert all(f.metadatos['doc_id']=='MANUAL-GRUPO' for f in retrieval.fragments)
    assert retrieval.manifest['modelo_embeddings']=='embeddings-simulados'
    assert retrieval.manifest['chunk_size_caracteres']==700 and retrieval.manifest['chunk_overlap_caracteres']==120
    assert retrieval.manifest['archivos']==[{'archivo':'manual_grupo.md',
        'sha256':hashlib.sha256(document.read_bytes()).hexdigest(),'fragmentos':len(retrieval.fragments)}]
    assert json.loads((tmp_path/'cache/corpus_manifest.json').read_text())==retrieval.manifest


def test_no_continua_silenciosamente_si_falta_el_manual(tmp_path):
    folder=tmp_path/'vacio';folder.mkdir()
    encoder=SimpleNamespace(model_id='simulado',encode=lambda texts:pytest.fail('No debe llamar embeddings sin documentos'))
    with pytest.raises(RuntimeError,match='documentos .md del manual'):
        Retrieval(encoder,folder,tmp_path/'cache')
