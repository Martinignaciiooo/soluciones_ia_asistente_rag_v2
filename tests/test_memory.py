"""Retención real en SQLite y uso de la clase de memoria indicada en clases."""
import json
from langchain_classic.memory import ConversationBufferWindowMemory
from src.storage import Store, WINDOW_MESSAGES, WINDOW_TURNS


def test_clase_real_guarda_y_carga_sqlite(tmp_path):
    store=Store(tmp_path/'memory.sqlite3')
    memory=store.memory('a','p')
    assert isinstance(memory,ConversationBufferWindowMemory)
    assert memory.k==5 and WINDOW_TURNS==5 and WINDOW_MESSAGES==10
    memory.save_context({'question':'¿Asistencia mínima?'},{'answer':'Consulta guardada.'})
    reopened=Store(store.path).memory('a','p')
    messages=reopened.load_memory_variables({})['history']
    assert [(m.type,m.content) for m in messages]==[
        ('human','¿Asistencia mínima?'),('ai','Consulta guardada.')]


def test_al_cruzar_10_mensajes_borra_los_dos_mas_antiguos(tmp_path):
    store=Store(tmp_path/'memory.sqlite3')
    for i in range(5):store.add_turn('a','p',f'pregunta-{i:03d}',f'respuesta-{i:03d}')
    assert len(store.context('a'))==10 and store.history('a')[0][0]=='pregunta-000'
    store.add_turn('a','p','pregunta-005','respuesta-005')
    with store.connect() as db:
        rows=db.execute('SELECT question,answer FROM turns WHERE session=? ORDER BY id',('a',)).fetchall()
    assert len(rows)==5 and rows[0]==('pregunta-001','respuesta-001')
    assert rows[-1]==('pregunta-005','respuesta-005')
    assert 'pregunta-000' not in json.dumps(rows)
    assert len(Store(store.path).context('a'))==10


def test_retencion_aislada_y_trazas_acotadas(tmp_path):
    store=Store(tmp_path/'memory.sqlite3')
    store.add_turn('b','p','historial de otra conversación','conservar')
    for i in range(40):
        store.add_turn('a','p',f'q{i}',f'a{i}')
        store.trace('a',{'consulta':f'q{i}'})
    assert store.history('b')==[('historial de otra conversación','conservar')]
    with store.connect() as db:
        traces=db.execute('SELECT data FROM traces WHERE session=? ORDER BY id',('a',)).fetchall()
    assert len(traces)==5 and json.loads(traces[0][0])['consulta']=='q35'


def test_migracion_no_reintroduce_memoria_antigua_ni_borra_gasto(tmp_path):
    store=Store(tmp_path/'memory.sqlite3')
    reservation=store.reserve(.02,.75)
    store.draft('a','solicitud-1','Borrador','Documento independiente del historial')
    with store.connect() as db:
        db.execute('CREATE TABLE memories (text TEXT)')
        db.execute('INSERT INTO memories VALUES (?)',('recuerdo antiguo',))
        db.executemany('INSERT INTO turns(session,profile,question,answer,created) VALUES (?,?,?,?,?)',
                       [('a','p',f'q{i}',f'a{i}','2026-01-01') for i in range(32)])
        db.executemany('INSERT INTO traces(session,data) VALUES (?,?)',
                       [('a',json.dumps({'consulta':f'q{i}'})) for i in range(32)])
    migrated=Store(store.path)
    assert len(migrated.history('a'))==5 and migrated.history('a')[0][0]=='q27'
    with migrated.connect() as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='memories'").fetchall()
        assert db.execute('SELECT COUNT(*) FROM traces').fetchone()[0]==5
        assert db.execute('SELECT id FROM usage').fetchone()[0]==reservation
    assert migrated.spent()==.02 and len(migrated.drafts('a'))==1


def test_clear_memoria_elimina_historial_y_trazas_de_esa_sesion(tmp_path):
    store=Store(tmp_path/'memory.sqlite3')
    for session in ('a','b'):
        store.add_turn(session,'p','pregunta','respuesta')
        store.trace(session,{'consulta':'pregunta'})
    store.memory('a','p').clear()
    assert not store.history('a') and store.history('b')
    with store.connect() as db:
        assert db.execute('SELECT session FROM traces').fetchall()==[('b',)]
