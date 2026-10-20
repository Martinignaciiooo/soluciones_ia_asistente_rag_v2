"""Integración opcional: TEST_DATABASE_URL debe apuntar a una base de pruebas.

Cada prueba usa y elimina un esquema propio; no toca el esquema asistentereg.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import uuid
import pytest
from psycopg import sql
from src.storage import Store
from scripts.probar_base_datos import verificar_base
from tests.test_agent import Agent,LexicalRetrieval,Scripted,call,draft_step,final_draft

@pytest.fixture
def pg():
    url=os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Sin TEST_DATABASE_URL: no se conecta a bases remotas durante los tests unitarios.')
    schema='test_'+uuid.uuid4().hex
    store=Store(url,schema=schema)
    try:
        yield store
    finally:
        with store.connect() as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_postgres_persistencia_retencion_y_aislamiento(pg):
    assert verificar_base(pg)['mensajes_conservados']==10
    pg.add_turn('otra','grupo','¿Asistencia?','Respuesta persistida')
    reopened=Store(pg._dsn,schema=pg.schema)
    assert reopened.history('otra')==[('¿Asistencia?','Respuesta persistida')]
    assert not reopened.history('nueva')


def test_postgres_borrador_idempotente_y_cache(pg):
    first=pg.draft('a','solicitud-1','Título','Contenido')
    second=pg.draft('a','solicitud-1','Otro','Otro')
    assert first==second and len(pg.drafts('a'))==1
    pg.save_embeddings({'modelo:texto':[1.,0.]})
    pg.save_embeddings({'modelo:texto':[0.,1.]})
    assert pg.cached_embeddings(['modelo:texto','no-existe'])=={'modelo:texto':[0.,1.]}


def test_postgres_presupuesto_compartido(pg):
    reservation=pg.reserve(.70,.75)
    other=Store(pg._dsn,schema=pg.schema)
    with pytest.raises(RuntimeError):other.reserve(.06,.75)
    other.settle(reservation,.01,100,50)
    assert pg.spent()==pytest.approx(.01)


def test_postgres_reservas_concurrentes_no_superan_tope(pg):
    def reserve(_):
        try:
            pg.reserve(.20,.75)
            return True
        except RuntimeError:
            return False
    with ThreadPoolExecutor(max_workers=4) as executor:
        accepted=list(executor.map(reserve,range(4)))
    assert sum(accepted)==3 and pg.spent()==pytest.approx(.60)


def test_postgres_trazas_y_flujo_completo_sin_api(pg):
    for i in range(7):pg.trace('prueba',{'consulta':f'consulta {i}'})
    with pg.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM traces WHERE session=%s',('prueba',)).fetchone()[0]==5
    provider=Scripted([call('buscar_normativa',consulta='retiro'),call('evaluar_plazo',tramite='retiro'),draft_step,final_draft])
    result=Agent(pg,LexicalRetrieval(),provider,today='2026-04-06').respond('Prepara un borrador para retiro de asignatura','flujo-pg')
    assert result['traza']['citas_validas'] and len(result['borradores'])==1
    assert pg.history('flujo-pg')[0][1]==result['respuesta']
