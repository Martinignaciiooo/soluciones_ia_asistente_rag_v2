"""Única conexión de IA: chat y embeddings mediante OpenRouter."""
from __future__ import annotations
import json,os,math,hashlib,re
from urllib.request import urlopen,Request
from .guardrails import anonimizar

MODEL='openai/gpt-6-luna'
EMBEDDING_MODEL='openai/text-embedding-3-small'
BASE_URL='https://openrouter.ai/api/v1'
MAX_INPUT_BYTES=24000
MAX_OUTPUT_TOKENS=1000

def api_error_details(error):
    """Extrae sólo estado y mensaje del error HTTP, sin request, headers ni secretos."""
    status=getattr(error,'status_code',None)
    if not isinstance(status,int):return {}
    out={'estado_http':status}
    body=getattr(error,'body',None)
    if not isinstance(body,dict):return out
    body=body.get('error',body)
    message=body.get('message') if isinstance(body,dict) else None
    if isinstance(message,str):
        for key in ('OPENROUTER_API_KEY','DATABASE_URL'):
            value=os.getenv(key)
            if value:message=message.replace(value,'[SECRETO_OCULTO]')
        message=re.sub(r'postgres(?:ql)?://\S+','[CONEXION_OCULTA]',message,flags=re.I)
        message=re.sub(r'\b(?:sk-[A-Za-z0-9_-]+|npg_[A-Za-z0-9_-]+)','[CLAVE_OCULTA]',message)
        out['mensaje_proveedor']=anonimizar(message)[0][:600]
    return out

class OpenRouter:
    mode='OpenRouter'
    def __init__(self,store,api_key=None,model=None,budget=None):
        from openai import OpenAI
        self.store=store
        self.model=model or os.getenv('OPENROUTER_MODEL',MODEL)
        self.embedding_model=os.getenv('OPENROUTER_EMBEDDING_MODEL',EMBEDDING_MODEL)
        self.cap=float(budget if budget is not None else os.getenv('LOCAL_BUDGET_USD','0.75'))
        key=api_key or os.getenv('OPENROUTER_API_KEY')
        if not key:raise RuntimeError('Falta OPENROUTER_API_KEY. Agrégala a .env o a Secrets de Colab.')
        self.client=OpenAI(api_key=key,base_url=BASE_URL,max_retries=0,timeout=35)
        self.prompt_price,self.completion_price=self.catalog_prices(self.model,api_key=key)
        self.embedding_price,_=self.catalog_prices(self.embedding_model,embeddings=True,api_key=key)
    @staticmethod
    def catalog_prices(model,embeddings=False,api_key=None):
        endpoint='/embeddings/models' if embeddings else '/models'
        request=Request(BASE_URL+endpoint,headers={'Authorization':'Bearer '+api_key} if api_key else {})
        with urlopen(request,timeout=20) as response:models=json.load(response)['data']
        item=next((m for m in models if m['id']==model),None)
        if not item:raise RuntimeError('Modelo ausente del catálogo. Confirma los IDs con el profesor.')
        if not embeddings and 'tools' not in item.get('supported_parameters',[]):
            raise RuntimeError('El modelo de chat no anuncia soporte de tools.')
        pricing=item['pricing']
        return float(pricing['prompt']),float(pricing.get('completion','0'))
    def invoke(self,messages,tools):
        messages=list(messages)
        self.last_trimmed_history_messages=0
        input_bytes=len(json.dumps({'messages':messages,'tools':tools},ensure_ascii=False).encode())
        # Sólo se omiten intercambios históricos completos, nunca el turno actual
        # ni pares tool_call/resultado. La ventana persistente conserva su límite.
        current_user=max((i for i,m in enumerate(messages) if m['role']=='user'),default=0)
        while input_bytes>MAX_INPUT_BYTES and current_user>2:
            if messages[1]['role']!='user' or messages[2]['role']!='assistant' or messages[2].get('tool_calls'):
                break
            del messages[1:3]
            current_user-=2
            self.last_trimmed_history_messages+=2
            input_bytes=len(json.dumps({'messages':messages,'tools':tools},ensure_ascii=False).encode())
        if input_bytes>MAX_INPUT_BYTES:raise RuntimeError('Contexto demasiado largo. Abre una conversación nueva o reduce la consulta.')
        reserve=(input_bytes+512)*self.prompt_price+MAX_OUTPUT_TOKENS*self.completion_price
        ident=self.store.reserve(reserve,self.cap)
        response=self.client.chat.completions.create(
            model=self.model,messages=messages,tools=tools,tool_choice='auto',
            max_tokens=MAX_OUTPUT_TOKENS,
            extra_body={'reasoning':{'effort':'low'},'provider':{'require_parameters':True}})
        usage=response.usage
        if usage and getattr(usage,'cost',None) is not None:
            self.store.settle(ident,float(usage.cost),usage.prompt_tokens,usage.completion_tokens)
        data=response.choices[0].message.model_dump(exclude_none=True)
        return {k:v for k,v in data.items() if k in ('role','content','tool_calls','reasoning_details')}
    def embed(self,texts):
        """Anonimiza y cachea antes de pedir vectores. Toda solicitud cuenta en el mismo tope."""
        clean=[anonimizar(str(t))[0] for t in texts]
        if not clean:return []
        if any(not t.strip() or len(t.encode())>6000 for t in clean):
            raise RuntimeError('Texto vacío o demasiado largo para embeddings.')
        keys=[hashlib.sha256((self.embedding_model+'\0'+t).encode()).hexdigest() for t in clean]
        cached=self.store.cached_embeddings(keys)
        missing={k:t for k,t in zip(keys,clean) if k not in cached}
        pairs=list(missing.items())
        for start in range(0,len(pairs),16):
            batch=pairs[start:start+16];inputs=[t for _,t in batch]
            reserve=(sum(len(t.encode()) for t in inputs)+512)*self.embedding_price
            ident=self.store.reserve(reserve,self.cap)
            response=self.client.embeddings.create(model=self.embedding_model,input=inputs,encoding_format='float')
            usage=response.usage
            if usage and getattr(usage,'cost',None) is not None:
                self.store.settle(ident,float(usage.cost),usage.prompt_tokens,0)
            # Si el endpoint omite coste, mantener la reserva conservadora y etiquetarla como tal.
            data=sorted(response.data,key=lambda d:d.index)
            if len(data)!=len(batch) or [d.index for d in data]!=list(range(len(batch))):
                raise RuntimeError('El proveedor devolvió un lote de vectores incompleto.')
            new={}
            for (key,_),item in zip(batch,data):
                vector=[float(x) for x in item.embedding]
                length=math.sqrt(sum(x*x for x in vector))
                if not vector or not math.isfinite(length) or length==0:raise RuntimeError('Vector inválido del proveedor.')
                new[key]=[x/length for x in vector]
            if len({len(v) for v in new.values()})!=1:raise RuntimeError('Dimensiones de vectores inconsistentes.')
            self.store.save_embeddings(new);cached.update(new)
        return [cached[k] for k in keys]

class OpenRouterEmbeddings:
    def __init__(self,provider):
        self.provider=provider;self.model_id=provider.embedding_model
    def encode(self,texts):return self.provider.embed(texts)
