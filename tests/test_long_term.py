import json
from src.agent import Agent, write_intent
from src.storage import Store
from src.long_term import buscar_borradores
from tests.test_agent import LexicalRetrieval, Scripted, call


def test_recupera_artefacto_tras_borrado_de_ventana_y_reinicio(tmp_path):
    ruta=tmp_path/'db.sqlite3'
    store=Store(ruta)
    store.draft('a','r1','Consulta de retiro','Borrador persistido para orientación.')
    for i in range(6):store.add_turn('a','p',f'pregunta-{i}',f'respuesta-{i}')
    assert 'pregunta-0' not in str(store.history('a'))
    def responder(messages):
        datos=json.loads(messages[-1]['content'])
        return {'role':'assistant','content':'Encontré tu borrador. '+datos['borradores'][0]['cita']}
    provider=Scripted([call('recuperar_borradores',consulta='borrador anterior de retiro'),responder])
    result=Agent(Store(ruta),LexicalRetrieval(),provider).respond('Recupera mi borrador anterior de retiro','a','p')
    assert result['traza']['citas_validas']
    assert result['traza']['memoria_largo_plazo']['recuperados']==1
    assert result['traza']['memoria_largo_plazo']['recupera_historial_eliminado'] is False
    assert 'pregunta-0' not in provider.prompts[0]
    assert len(store.drafts('a'))==1 and not write_intent('Recupera mi borrador anterior')
    assert not write_intent('Muestra mi borrador guardado de retiro')


def test_no_cruza_conversaciones_ni_llama_embeddings_sin_borradores(tmp_path):
    store=Store(tmp_path/'db.sqlite3');store.draft('a','r1','Privado','Dato de otra conversación')
    retrieval=LexicalRetrieval()
    retrieval.encoder.encode=lambda _: (_ for _ in ()).throw(AssertionError('No debe llamar embeddings'))
    state={'query':'Recupera mi borrador anterior','session':'b','evidence':{},'trace':{}}
    tool=next(t for t in Agent(store,retrieval,Scripted([])).tools(state) if t.name=='recuperar_borradores')
    assert tool.invoke({'consulta':'retiro'})['sin_resultados']
    assert not state['evidence']


def test_umbral_semantico_rechaza_artefactos_ajenos():
    class Encoder:
        def encode(self,textos):return [[1.,0.],[0.,1.],[1.,0.]]
    result=buscar_borradores(Encoder(),[(2,'Suspensión','texto'),(1,'Retiro','texto')],'retiro')
    assert [r['id'] for r in result]==[1]
    assert result[0]['fuente_es_normativa'] is False


def test_lectura_acotada_de_borradores(tmp_path):
    store=Store(tmp_path/'db.sqlite3')
    for i in range(23):store.draft('a',f'r{i}',f'Título {i}','Cuerpo')
    assert len(store.drafts('a',limit=200))==20
    assert store.drafts('a',limit=2)[0][1]=='Título 22'
