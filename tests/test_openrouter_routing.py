"""Regresión de routing con el SDK real y transporte HTTP simulado; sin saldo."""
import json
from types import SimpleNamespace
import httpx
from openai import OpenAI,NotFoundError
from src.provider import OpenRouter,api_error_details
from src.storage import Store
from src.agent import Agent
from tests.test_agent import LexicalRetrieval


def test_payload_compatible_con_endpoints_luna_y_effort_low(tmp_path):
    supported={'reasoning','include_reasoning','seed','max_tokens','response_format',
               'structured_outputs','tools','tool_choice','verbosity','reasoning_effort'}
    payloads=[]
    def endpoint(request):
        payload=json.loads(request.content);payloads.append(payload)
        unsupported=set(payload)-supported-{'model','messages','provider'}
        if payload.get('provider',{}).get('require_parameters') and unsupported:
            return httpx.Response(404,json={'error':{'message':'No endpoints found that can handle the requested parameters','code':404}})
        return httpx.Response(200,json={
            'id':'simulado','object':'chat.completion','created':0,'model':'openai/gpt-6-luna',
            'choices':[{'index':0,'message':{'role':'assistant','content':'ok'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12,'cost':0.000002}})
    p=OpenRouter.__new__(OpenRouter)
    p.store=Store(tmp_path/'db.sqlite3');p.model='openai/gpt-6-luna';p.cap=.75
    p.prompt_price=.1/1_000_000;p.completion_price=.5/1_000_000
    p.client=OpenAI(api_key='clave-ficticia',base_url='https://openrouter.invalid/api/v1',max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(endpoint)))
    try:
        result=p.invoke([{'role':'user','content':'hola'}],[])
        assert result['content']=='ok' and len(payloads)==1
        assert payloads[0]['reasoning']=={'effort':'low'}
        assert payloads[0]['provider']['require_parameters'] is True
        assert p.store.spent()==0.000002
    finally:p.client.close()


def test_404_muestra_causa_sin_exponer_credenciales(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','clave-privada-del-grupo')
    request=httpx.Request('POST','https://openrouter.invalid/api/v1/chat/completions')
    response=httpx.Response(404,request=request)
    error=NotFoundError('No endpoints',response=response,body={'error':{'message':
        'No endpoints found. clave-privada-del-grupo sk-or-no-publicar npg_no_publicar '
        'postgresql://usuario:password@host/base prueba@example.com'}})
    class Broken:
        model='openai/gpt-6-luna'
        def invoke(self,*args):raise error
    result=Agent(Store(tmp_path/'db.sqlite3'),LexicalRetrieval(),Broken()).respond('asistencia mínima')
    trace=result['traza'];serialized=json.dumps(result)
    assert trace['estado_http']==404 and 'No endpoints found' in trace['mensaje_proveedor']
    assert trace['intentos_llamada']==1 and trace['llamadas']==0
    assert 'endpoint compatible' in result['respuesta']
    for secret in ['clave-privada-del-grupo','sk-or-no-publicar','npg_no_publicar','password','prueba@example.com']:
        assert secret not in serialized


def test_excepcion_sin_http_no_revela_su_texto():
    assert api_error_details(ValueError('sk-or-no-publicar'))=={}


def test_mensaje_http_incompleto_se_maneja_sin_error():
    assert api_error_details(SimpleNamespace(status_code=404,body=None))=={'estado_http':404}
