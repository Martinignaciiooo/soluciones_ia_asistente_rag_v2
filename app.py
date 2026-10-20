"""Interfaz de AsistenteReg: todos los modelos se consumen vía OpenRouter."""
from datetime import date
import os,uuid
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.agent import Agent
from src.provider import OpenRouter,OpenRouterEmbeddings
from src.retrieval import Retrieval
from src.storage import Store, StorageError, WINDOW_MESSAGES

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
st.set_page_config(page_title='AsistenteReg EP2',page_icon='📚',layout='wide')
st.title('AsistenteReg')
st.caption('Registro Curricular · EP2 · Martín Peña y Valentina')
st.info('Escenario académico con documentos sintéticos de 2026-01. Las respuestas y los embeddings se solicitan a OpenRouter.')
missing=[name for name in ('OPENROUTER_API_KEY','DATABASE_URL') if not os.getenv(name)]
if missing:
    st.warning('Falta configurar '+', '.join(missing)+'. Agrégalas en .env y reinicia la aplicación.')
    st.stop()
if 'store' not in st.session_state:
    try:st.session_state.store=Store()
    except Exception as exc:
        st.error('No se pudo conectar a PostgreSQL. Revisa DATABASE_URL y los permisos de la base. Tipo: '+type(exc).__name__)
        st.stop()
store=st.session_state.store

# La caché PostgreSQL se comparte entre sesiones y equipos del grupo.
if 'provider' not in st.session_state:
    try:st.session_state.provider=OpenRouter(store)
    except Exception as exc:
        st.error('No se pudo configurar OpenRouter. Revisa la conexión, la clave y los modelos configurados. Tipo: '+type(exc).__name__)
        st.stop()
if 'retrieval' not in st.session_state:
    with st.spinner('Preparando el índice con embeddings de OpenRouter…'):
        try:st.session_state.retrieval=Retrieval(OpenRouterEmbeddings(st.session_state.provider),cache_dir=ROOT/'runtime')
        except Exception as exc:
            st.error('No se pudo preparar el índice. Revisa permisos de embeddings, saldo y conexión. Tipo: '+type(exc).__name__)
            st.stop()

with st.sidebar:
    st.header('Conversación y escenario')
    profile=st.text_input('Perfil anónimo','grupo-ep2')
    if 'session' not in st.session_state:st.session_state.session='demo-'+uuid.uuid4().hex[:8]
    session=st.text_input('ID de conversación',key='session')
    st.caption('Reabre este ID para recuperar el historial.')
    simulate=st.checkbox('Simular fecha del semestre 2026-01',value=True)
    today=st.date_input('Fecha simulada',value=date(2026,4,6),min_value=date(2026,3,2),max_value=date(2026,7,18)) if simulate else date.today()
    st.write('Fecha usada:',today.isoformat())
    st.metric('Consumo o reservas del proyecto',f'USD {store.spent():.6f}')
    st.caption('Tope compartido en esta base: USD '+os.getenv('LOCAL_BUDGET_USD','0.75')+'. Revisa el saldo real en OpenRouter.')
    st.caption(f'Memoria stateful: ConversationBufferWindowMemory, hasta {WINDOW_MESSAGES} mensajes por conversación en PostgreSQL. Los más antiguos se eliminan automáticamente.')
    st.caption('Borradores guardados por separado. Versión de demostración sin autenticación.')

for q,a in store.history(session):
    with st.chat_message('user'):st.write(q)
    with st.chat_message('assistant'):st.write(a)
query=st.chat_input('¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta.')
if query:
    with st.spinner('Consultando OpenRouter y ejecutando herramientas…'):
        try:result=Agent(store,st.session_state.retrieval,st.session_state.provider,today=today.isoformat()).respond(query,session,profile)
        except StorageError:
            st.error('Se interrumpió la conexión a PostgreSQL. Revisa la base antes de volver a consultar.')
            st.stop()
    st.session_state.last_trace=result['traza'];st.rerun()
with st.expander('Plan y herramientas del último turno'):
    if 'last_trace' in st.session_state:st.json(st.session_state.last_trace)
    else:st.write('El plan aparecerá después de consultar.')
with st.expander('Borradores guardados'):
    drafts=store.drafts(session)
    if not drafts:st.write('No hay borradores en esta conversación.')
    for ident,title,body in drafts:
        st.subheader(f'#{ident} {title}');st.write(body)
        st.download_button('Descargar borrador',body,file_name=f'borrador_{ident}.txt',key=f'draft-{ident}')
