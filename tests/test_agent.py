"""Integración determinista SIN claves ni gasto. Los dobles no prueban calidad del LLM real."""
import json
from pathlib import Path
import pytest
from src.agent import Agent,ABSTAIN
from src.storage import Store
from src.retrieval import Retrieval
from src.provider import OpenRouter,MAX_INPUT_BYTES

class Encoder:
    model_id='doble-pruebas-v1'
    def encode(self,texts):return [[1.,0.] for _ in texts]

class Scripted:
    def __init__(self,steps):self.steps=iter(steps);self.prompts=[]
    def invoke(self,messages,tools):
        self.prompts.append(json.dumps(messages,ensure_ascii=False))
        step=next(self.steps)
        return step(messages) if callable(step) else step

def call(name,**args):
    return {'role':'assistant','tool_calls':[{'id':'call-'+name,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}

def sourced(messages):
    for m in reversed(messages):
        if m['role']=='tool':
            data=json.loads(m['content'])
            if data.get('documentos'):
                return {'role':'assistant','content':'La asistencia regular es 70%. '+data['documentos'][0]['cita']}
    raise AssertionError('sin documento')

class LexicalRetrieval:
    def __init__(self):
        from src.ingest import cargar_corpus
        from src.lexical import RecuperadorLexico
        self.fragments=cargar_corpus(Path(__file__).resolve().parents[1]/'data/interna')
        self.lex=RecuperadorLexico(self.fragments);self.encoder=Encoder()
    def search(self,query,k=3):return self.lex.buscar(query,k)

@pytest.fixture
def env(tmp_path):return Store(tmp_path/'db.sqlite3'),LexicalRetrieval()

def run(env,steps,q='¿Cuál es la asistencia mínima?',today='2026-04-06',session='a',profile='p'):
    store,retrieval=env;provider=Scripted(steps)
    result=Agent(store,retrieval,provider,today=today).respond(q,session,profile)
    return result,provider

def test_fuera_de_alcance_no_consume(env):
    r,p=run(env,[],'¿Cuál es el precio del bitcoin?')
    assert r['respuesta']==ABSTAIN and not p.prompts

def test_cita_obligatoria(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),{'role':'assistant','content':'Es 70%.'}])
    assert r['respuesta']==ABSTAIN and not r['traza']['citas_validas']

def test_cita_inventada_se_bloquea(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),{'role':'assistant','content':'70% [REG-INVENTADO, Artículo 1, v4.2]'}])
    assert r['respuesta']==ABSTAIN

def test_cita_seccion_inventada_se_bloquea(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),{'role':'assistant','content':'70% [REG-ACAD-2026, Artículo 999, v4.2]'}])
    assert r['respuesta']==ABSTAIN

def test_respuesta_citada_y_persistencia(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),sourced])
    assert r['traza']['citas_validas']
    assert Store(env[0].path).history('a')[0][1]==r['respuesta']

def test_pii_ausente_de_prompts_historial_trazas(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),sourced],'Mi RUT es 18.456.789-2 y correo prueba@example.com, ¿cuál es la asistencia mínima?')
    content=''.join(p.prompts)+json.dumps(env[0].history('a'))+json.dumps(r)
    assert '18.456.789-2' not in content and 'prueba@example.com' not in content

def test_memoria_no_cruza_conversaciones(env):
    run(env,[call('buscar_normativa',consulta='asistencia mínima'),sourced])
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),sourced],session='b')
    assert r['traza']['clase_memoria']=='ConversationBufferWindowMemory'
    assert r['traza']['mensajes_memoria']==0

def test_agente_recibe_ventana_sin_resumen_ni_recuerdos_eliminados(env):
    store,_=env
    for i in range(6):store.add_turn('a','p',f'consulta-{i:03d}',f'respuesta-{i:03d}')
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima'),sourced])
    assert r['traza']['mensajes_memoria']==10
    assert r['traza']['turnos_recientes']==5
    assert 'consulta-000' not in p.prompts[0] and 'consulta-001' in p.prompts[0]
    assert 'resumen_extractivo' not in p.prompts[0] and 'memoria_semantica' not in p.prompts[0]

def test_limite_de_cuatro_llamadas(env):
    r,p=run(env,[call('buscar_normativa',consulta='asistencia mínima')]*4)
    assert len(p.prompts)==4 and r['traza']['llamadas']==4

def test_herramienta_no_registrada_no_se_ejecuta(env):
    r,p=run(env,[call('borrar_base'),{'role':'assistant','content':ABSTAIN}])
    assert r['traza']['herramientas'][0]['resultado']['error']=='Herramienta no registrada.'

def test_json_malformado_es_observacion(env):
    bad=call('buscar_normativa',consulta='asistencia');bad['tool_calls'][0]['function']['arguments']='{'
    r,p=run(env,[bad,{'role':'assistant','content':ABSTAIN}])
    assert r['traza']['herramientas'][0]['resultado']['tipo']=='JSONDecodeError'

@pytest.mark.parametrize('today,status',[('2026-04-06','vigente'),('2026-04-11','vencido'),('2026-04-10','vigente')])
def test_plan_se_adapta_al_plazo(env,today,status):
    r,p=run(env,[call('evaluar_plazo',tramite='retiro'),{'role':'assistant','content':ABSTAIN}],q='retiro de asignatura',today=today)
    assert r['traza']['decisiones'][0]['plazo']==status

def test_calendario_historico_se_declara(env):
    r,p=run(env,[call('evaluar_plazo',tramite='retiro'),{'role':'assistant','content':ABSTAIN}],q='retiro de asignatura',today='2026-10-19')
    assert r['traza']['herramientas'][0]['resultado']['calendario_aplicable'] is False

def test_escritura_sin_intencion_se_rechaza(env):
    r,p=run(env,[call('guardar_borrador',titulo='x',cuerpo='x'),{'role':'assistant','content':ABSTAIN}])
    assert not r['borradores']

def test_escritura_sin_evidencia_se_rechaza(env):
    r,p=run(env,[call('guardar_borrador',titulo='x',cuerpo='x'),{'role':'assistant','content':ABSTAIN}],q='Redacta borrador de retiro')
    assert not r['borradores']

def draft_step(messages):
    docs=json.loads(next(m['content'] for m in messages if m['role']=='tool' and 'documentos' in m['content']))['documentos']
    return call('guardar_borrador',titulo='Consulta sobre retiro',cuerpo='Solicito orientación para retirar una asignatura. '+docs[0]['cita'])

def final_draft(messages):
    cite=json.loads(next(m['content'] for m in messages if m['role']=='tool' and 'documentos' in m['content']))['documentos'][0]['cita']
    return {'role':'assistant','content':'Se preparó una consulta con respaldo. '+cite}

def test_flujo_completo_borrador(env):
    r,p=run(env,[call('buscar_normativa',consulta='retiro asignaturas'),call('evaluar_plazo',tramite='retiro'),draft_step,final_draft],q='Prepara un borrador para retiro de asignatura')
    assert r['traza']['citas_validas'] and len(r['borradores'])==1
    assert r['traza']['llamadas']==4 and 'guardado #1' in r['respuesta']

def test_escritura_idempotente_por_solicitud(env):
    store,_=env
    a=store.draft('a','request-1','titulo','texto');b=store.draft('a','request-1','otro','otro')
    assert a==b and len(store.drafts('a'))==1

def test_reserva_se_bloquea_al_superar_tope(env):
    store,_=env;ident=store.reserve(.7,.75)
    with pytest.raises(RuntimeError):store.reserve(.06,.75)
    store.settle(ident,.1,100,100)
    assert store.spent()==pytest.approx(.1)

def test_provider_request_sin_red_y_parametros_de_ahorro(env):
    from types import SimpleNamespace
    store,_=env;provider=OpenRouter.__new__(OpenRouter)
    provider.store=store;provider.model='openai/gpt-6-luna';provider.cap=.75
    provider.prompt_price=.1/1_000_000;provider.completion_price=.5/1_000_000
    captured={}
    def create(**kw):
        captured.update(kw)
        msg=SimpleNamespace(model_dump=lambda **_: {'role':'assistant','content':'ok'})
        return SimpleNamespace(usage=SimpleNamespace(cost=.0001,prompt_tokens=30,completion_tokens=10),choices=[SimpleNamespace(message=msg)])
    provider.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider.invoke([{'role':'user','content':'hola'}],[])
    assert captured['extra_body']['reasoning']['effort']=='low'
    assert captured['max_tokens']==1000 and 'parallel_tool_calls' not in captured
    assert captured['extra_body']['provider']['require_parameters'] is True
    assert store.spent()==pytest.approx(.0001)
    with pytest.raises(RuntimeError):provider.invoke([{'role':'user','content':'x'*(MAX_INPUT_BYTES+1)}],[])

def test_error_api_no_expone_secretos(env):
    class Broken:
        def invoke(self,*args):raise ValueError('sk-or-secret-no-publicar')
    r=Agent(env[0],env[1],Broken()).respond('asistencia mínima')
    assert 'sk-or-secret' not in json.dumps(r)

def test_entrada_larga_omite_historial_sin_romper_herramientas(env):
    from types import SimpleNamespace
    provider=OpenRouter.__new__(OpenRouter)
    provider.store=env[0];provider.model='openai/gpt-6-luna';provider.cap=.75
    provider.prompt_price=.1/1_000_000;provider.completion_price=.5/1_000_000
    captured={}
    def create(**kw):
        captured.update(kw)
        msg=SimpleNamespace(model_dump=lambda **_: {'role':'assistant','content':'ok'})
        return SimpleNamespace(usage=None,choices=[SimpleNamespace(message=msg)])
    provider.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    messages=[{'role':'system','content':'Control del agente'}]
    for i in range(25):
        messages.extend([{'role':'user','content':f'pregunta-{i} '+'q'*600},
                         {'role':'assistant','content':f'respuesta-{i} '+'a'*600}])
    active=[{'role':'user','content':'Consulta vigente'},call('buscar_normativa',consulta='asistencia'),
            {'role':'tool','tool_call_id':'call-buscar_normativa','content':'Resultado de normativa'}]
    messages.extend(active)
    original=json.dumps(messages)
    provider.invoke(messages,[])
    sent=captured['messages']
    assert json.dumps(messages)==original
    assert sent[0]==messages[0] and sent[-3:]==active
    assert provider.last_trimmed_history_messages>0
    assert len(json.dumps({'messages':sent,'tools':[]},ensure_ascii=False).encode())<=MAX_INPUT_BYTES
