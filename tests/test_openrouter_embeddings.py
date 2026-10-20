"""Contrato de embeddings OpenRouter probado con SDK simulado, sin red ni saldo."""
from types import SimpleNamespace
import pytest
from src.provider import OpenRouter,OpenRouterEmbeddings
from src.storage import Store
from src.retrieval import Retrieval

def setup(tmp_path,create):
    p=OpenRouter.__new__(OpenRouter);p.store=Store(tmp_path/'db.sqlite3');p.cap=.75
    p.embedding_model='openai/text-embedding-3-small';p.embedding_price=.02/1_000_000
    p.client=SimpleNamespace(embeddings=SimpleNamespace(create=create))
    return p

def response(vectors,cost=None):
    usage=SimpleNamespace(prompt_tokens=20,cost=cost)
    return SimpleNamespace(data=[SimpleNamespace(index=i,embedding=v) for i,v in enumerate(vectors)],usage=usage)

def test_normaliza_cachea_y_deduplica(tmp_path):
    calls=[]
    def create(**kw):calls.append(kw);return response([[3.,4.]])
    p=setup(tmp_path,create)
    assert p.embed(['consulta','consulta'])==[[.6,.8],[.6,.8]]
    assert p.embed(['consulta'])==[[.6,.8]]
    assert len(calls)==1 and calls[0]['model']=='openai/text-embedding-3-small'

def test_cache_se_conserva_al_reabrir_base(tmp_path):
    p=setup(tmp_path,lambda **kw:response([[1.,0.]]));p.embed(['consulta'])
    def no_network(**kw):raise AssertionError('No debería llamar a la API')
    q=setup(tmp_path,no_network)
    assert q.embed(['consulta'])==[[1.,0.]]

def test_pii_no_sale_hacia_embeddings(tmp_path):
    sent=[]
    def create(**kw):sent.extend(kw['input']);return response([[1.,0.]])
    p=setup(tmp_path,create);p.embed(['Mi RUT 18.456.789-2 y correo prueba@example.com'])
    assert '18.456.789-2' not in sent[0] and 'prueba@example.com' not in sent[0]

def test_embeddings_comparten_el_tope(tmp_path):
    p=setup(tmp_path,lambda **kw:response([[1.,0.]]));p.store.reserve(.75,.75)
    with pytest.raises(RuntimeError):p.embed(['consulta'])

def test_error_de_red_conserva_reserva_y_no_reintenta(tmp_path):
    calls=[]
    def broken(**kw):calls.append(kw);raise ConnectionError('error simulado')
    p=setup(tmp_path,broken)
    with pytest.raises(ConnectionError):p.embed(['consulta'])
    assert len(calls)==1 and p.store.spent()>0

def test_registra_coste_reportado(tmp_path):
    p=setup(tmp_path,lambda **kw:response([[1.,0.]],.00001));p.embed(['consulta'])
    assert p.store.spent()==pytest.approx(.00001)

def test_cache_separa_modelos(tmp_path):
    calls=[]
    def create(**kw):calls.append(kw);return response([[1.,0.]])
    p=setup(tmp_path,create);p.embed(['consulta']);p.embedding_model='otro-modelo';p.embed(['consulta'])
    assert len(calls)==2

def test_rechaza_lotes_incompletos(tmp_path):
    p=setup(tmp_path,lambda **kw:response([]))
    with pytest.raises(RuntimeError):p.embed(['consulta'])

def test_indice_reutiliza_vectores_y_se_invalida_al_cambiar_corpus(tmp_path):
    folder=tmp_path/'corpus';folder.mkdir()
    doc=folder/'norma.md';doc.write_text('---\ndoc_id: NORM-1\nversion: 1\n---\n\n## Asistencia\nLa asistencia mínima es 70%.')
    class Encoder:
        model_id='api-simulada'
        def __init__(self):self.calls=[]
        def encode(self,texts):self.calls.append(texts);return [[1.,0.] for t in texts]
    e=Encoder();cache=tmp_path/'cache'
    Retrieval(e,folder,cache);Retrieval(e,folder,cache)
    assert len(e.calls)==1
    doc.write_text(doc.read_text()+'\nCambio normativo.')
    Retrieval(e,folder,cache)
    assert len(e.calls)==2
