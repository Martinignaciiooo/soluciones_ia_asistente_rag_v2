"""Memoria en PostgreSQL; SQLite explícito para pruebas sin red."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

WINDOW_MESSAGES = 10
WINDOW_TURNS = WINDOW_MESSAGES // 2


class StorageError(RuntimeError):
    """Error de almacenamiento sin credenciales en su mensaje."""


class PersistentWindowHistory(BaseChatMessageHistory):
    def __init__(self, store, session, profile):
        self.store, self.session, self.profile = store, session, profile

    @property
    def messages(self):
        out = []
        for question, answer in self.store.history(self.session):
            out.extend([HumanMessage(content=question), AIMessage(content=answer)])
        return out

    def add_messages(self, messages):
        if len(messages) != 2 or not isinstance(messages[0], HumanMessage) or not isinstance(messages[1], AIMessage):
            raise ValueError('La memoria guarda pares completos de pregunta y respuesta final.')
        self.store._append_turn(self.session, self.profile, messages[0].content, messages[1].content)

    def clear(self):
        self.store.clear_history(self.session)


class Store:
    def __init__(self, path=None, *, schema='asistentereg'):
        # Store() exige DATABASE_URL. Una ruta SQLite explícita sirve a los tests.
        target = str(path) if path is not None else os.getenv('DATABASE_URL', '').strip()
        self.schema = schema
        self.path = None
        if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', schema):
            raise ValueError('Nombre de esquema inválido.')
        if not target:
            raise StorageError('Falta DATABASE_URL. Agrégala a Secrets de Colab o a .env.')
        if target.startswith(('postgresql://', 'postgres://')):
            self.backend = 'postgresql'
            self._dsn = target
            try:
                params = conninfo_to_dict(target)
            except (psycopg.Error, ValueError):
                raise StorageError('DATABASE_URL inválida. Pega sólo la URL PostgreSQL, sin psql ni comillas.') from None
            self._ssl = {} if 'sslmode' in params else {'sslmode': 'require'}
            if params.get('host') not in ('localhost', '127.0.0.1', '::1') and params.get('sslmode') in ('disable', 'allow', 'prefer'):
                raise StorageError('La conexión remota debe usar sslmode=require o verificación de certificado.')
        elif path is not None and (isinstance(path, Path) or target.endswith(('.sqlite3', '.sqlite', '.db'))):
            self.backend = 'sqlite'
            self.path = Path(target)
            self.path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise StorageError('DATABASE_URL debe comenzar con postgresql:// o postgres://.')
        self._initialize()

    @contextmanager
    def connect(self):
        db = None
        try:
            if self.backend == 'postgresql':
                db = psycopg.connect(self._dsn, connect_timeout=15, prepare_threshold=None, **self._ssl)
                db.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(self.schema)))
                db.execute("SET LOCAL lock_timeout TO '10s'")
                db.execute("SET LOCAL statement_timeout TO '15s'")
            else:
                db = sqlite3.connect(self.path, timeout=15)
            yield db
            db.commit()
        except psycopg.Error as error:
            if db is not None:
                try:db.rollback()
                except psycopg.Error:pass
            raise StorageError('No se pudo operar con PostgreSQL. Revisa DATABASE_URL, conexión y permisos. Tipo: '+type(error).__name__) from None
        except Exception:
            if db is not None:
                try:db.rollback()
                except psycopg.Error:pass
            raise
        finally:
            if db is not None:
                db.close()

    def _execute(self, db, statement, parameters=()):
        # Plantillas internas únicamente; los valores siempre se parametrizan.
        if self.backend == 'postgresql':
            statement = statement.replace('?', '%s')
        return db.execute(statement, parameters)

    def _lock(self, db, resource):
        if self.backend == 'postgresql':
            key = int.from_bytes(hashlib.sha256((self.schema+':'+resource).encode()).digest()[:8], 'big', signed=True)
            self._execute(db, 'SELECT pg_advisory_xact_lock(?)', (key,))
        else:
            db.execute('BEGIN IMMEDIATE')

    def _initialize(self):
        with self.connect() as db:
            self._lock(db, 'schema')
            if self.backend == 'postgresql':
                db.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(self.schema)))
            identity = 'BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY' if self.backend == 'postgresql' else 'INTEGER PRIMARY KEY'
            amount_type = 'NUMERIC(18,9)' if self.backend == 'postgresql' else 'REAL'
            for statement in [
                f'CREATE TABLE IF NOT EXISTS turns(id {identity}, session TEXT, profile TEXT, question TEXT, answer TEXT, created TEXT)',
                f'CREATE TABLE IF NOT EXISTS drafts(id {identity}, session TEXT, request_id TEXT UNIQUE, title TEXT, body TEXT, created TEXT)',
                f'CREATE TABLE IF NOT EXISTS usage(id {identity}, amount {amount_type}, state TEXT, prompt_tokens INTEGER DEFAULT 0, completion_tokens INTEGER DEFAULT 0, created TEXT)',
                f'CREATE TABLE IF NOT EXISTS traces(id {identity}, session TEXT, data TEXT)',
                'CREATE TABLE IF NOT EXISTS embedding_cache(key TEXT PRIMARY KEY, vector TEXT)',
                'CREATE INDEX IF NOT EXISTS turns_session_id ON turns(session,id)',
                'CREATE INDEX IF NOT EXISTS traces_session_id ON traces(session,id)',
            ]:
                db.execute(statement)
            if self.backend == 'sqlite':
                db.execute('DROP TABLE IF EXISTS memories')
            for table in ('turns', 'traces'):
                for (session,) in db.execute(f'SELECT DISTINCT session FROM {table}').fetchall():
                    self._prune(db, table, session)

    def history(self, session):
        with self.connect() as db:
            return self._execute(db, 'SELECT question,answer FROM turns WHERE session=? ORDER BY id', (session,)).fetchall()

    def memory(self, session, profile='estudiante-demo'):
        return ConversationBufferWindowMemory(
            k=WINDOW_TURNS, return_messages=True,
            input_key='question', output_key='answer', memory_key='history',
            chat_memory=PersistentWindowHistory(self, session, profile),
        )

    def context(self, session):
        return [{'role': 'user' if m.type == 'human' else 'assistant', 'content': m.content}
                for m in self.memory(session).load_memory_variables({})['history']]

    def _prune(self, db, table, session):
        if table not in ('turns', 'traces'):
            raise ValueError('Tabla de memoria inválida.')
        self._execute(db, f'''DELETE FROM {table} WHERE session=? AND id NOT IN
            (SELECT id FROM {table} WHERE session=? ORDER BY id DESC LIMIT ?)''',
            (session, session, WINDOW_TURNS))

    def add_turn(self, session, profile, question, answer):
        self.memory(session, profile).save_context({'question': question}, {'answer': answer})

    def _append_turn(self, session, profile, question, answer):
        with self.connect() as db:
            self._lock(db, 'session:'+session)
            self._execute(db, 'INSERT INTO turns(session,profile,question,answer,created) VALUES(?,?,?,?,?)',
                          (session, profile, question, answer, datetime.now(timezone.utc).isoformat()))
            self._prune(db, 'turns', session)

    def clear_history(self, session):
        with self.connect() as db:
            self._lock(db, 'session:'+session)
            self._execute(db, 'DELETE FROM turns WHERE session=?', (session,))
            self._execute(db, 'DELETE FROM traces WHERE session=?', (session,))

    def draft(self, session, request_id, title, body):
        with self.connect() as db:
            self._execute(db, '''INSERT INTO drafts(session,request_id,title,body,created) VALUES(?,?,?,?,?)
                ON CONFLICT(request_id) DO NOTHING''',
                (session, request_id, title, body, datetime.now(timezone.utc).isoformat()))
            return self._execute(db, 'SELECT id,title,body FROM drafts WHERE request_id=?', (request_id,)).fetchone()

    def drafts(self, session, limit=None):
        with self.connect() as db:
            sql = 'SELECT id,title,body FROM drafts WHERE session=? ORDER BY id DESC'
            params = (session,)
            if limit is not None:
                sql += ' LIMIT ?'
                params += (max(1, min(int(limit), 20)),)
            return self._execute(db, sql, params).fetchall()

    def spent(self):
        with self.connect() as db:
            return float(db.execute('SELECT COALESCE(SUM(amount),0) FROM usage').fetchone()[0])

    def reserve(self, amount, cap):
        with self.connect() as db:
            self._lock(db, 'budget')
            spent = float(db.execute('SELECT COALESCE(SUM(amount),0) FROM usage').fetchone()[0])
            if spent+amount > cap:
                raise RuntimeError('Tope de presupuesto del proyecto alcanzado. Revisa consumo y saldo antes de continuar.')
            return self._execute(db, 'INSERT INTO usage(amount,state,created) VALUES(?,?,?) RETURNING id',
                                 (amount, 'reserva', datetime.now(timezone.utc).isoformat())).fetchone()[0]

    def settle(self, ident, amount, prompt=0, completion=0):
        with self.connect() as db:
            self._lock(db, 'budget')
            self._execute(db, 'UPDATE usage SET amount=?,state=?,prompt_tokens=?,completion_tokens=? WHERE id=?',
                          (amount, 'reportado', prompt, completion, ident))

    def trace(self, session, trace):
        with self.connect() as db:
            self._lock(db, 'session:'+session)
            self._execute(db, 'INSERT INTO traces(session,data) VALUES(?,?)', (session, json.dumps(trace, ensure_ascii=False)))
            self._prune(db, 'traces', session)

    def cached_embeddings(self, keys):
        if not keys:
            return {}
        keys = sorted(set(keys))
        with self.connect() as db:
            rows = self._execute(db, 'SELECT key,vector FROM embedding_cache WHERE key IN ('+','.join('?' for _ in keys)+')', tuple(keys)).fetchall()
        return {key: json.loads(vector) for key, vector in rows}

    def save_embeddings(self, items):
        statement = 'INSERT INTO embedding_cache(key,vector) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET vector=excluded.vector'
        if self.backend == 'postgresql':
            statement = statement.replace('?', '%s')
        with self.connect() as db:
            cursor = db.cursor()
            try:
                cursor.executemany(statement, [(key, json.dumps(vector)) for key, vector in items.items()])
            finally:
                cursor.close()
