# AsistenteReg EP2 con OpenRouter

Repositorio de entrega: [soluciones_ia_asistente_rag_v2](https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2).

Agente para Registro Curricular. Todos los modelos se consumen mediante una única API de OpenRouter y la clave del grupo. La aplicación usa LangGraph para la orquestación, herramientas de LangChain y PostgreSQL remoto para el historial y los borradores.

- Chat y tools: `openai/gpt-6-luna`, razonamiento `low`.
- Búsqueda semántica de normativa: `openai/text-embedding-3-small`, mediante el endpoint `/embeddings` de OpenRouter.
- No hay instalación, descarga ni ejecución de modelos locales. No se requiere GPU.

Los cuatro documentos de `data/interna` son sintéticos y corresponden al semestre 2026-01. La aplicación identifica la fecha de simulación y no aprueba trámites ni envía correos.

## Windows

1. Instalar Python 3.11 o 3.12 y extraer la carpeta completa del proyecto.
2. Abrir `iniciar.bat`.
3. Ingresar `OPENROUTER_API_KEY` y `DATABASE_URL` en `.env`, guardar y cerrar el Bloc. La segunda variable es la URL PostgreSQL de Neon o Supabase.
4. Abrir http://127.0.0.1:8501 si el navegador no se abre automáticamente.

En el primer arranque se generan los embeddings del corpus mediante la API. Las respuestas y los embeddings consumen el presupuesto del grupo. En los arranques siguientes se reutiliza la caché si el corpus y el modelo no cambiaron.

## Instalación manual

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux o macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
# Copiar .env.example a .env y configurar OPENROUTER_API_KEY y DATABASE_URL.
python -m pytest tests -q
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Las pruebas usan dobles de la API y no consumen saldo. La comprobación real debe ejecutarse de forma manual:

```bash
python scripts/probar_openrouter.py
```

La comprobación de PostgreSQL (`python scripts/probar_base_datos.py`) no usa modelos. La prueba de OpenRouter sí usa embeddings y chat de OpenRouter, y guarda evidencia en `docs/evidencias/prueba_real_openrouter.json`. Confirmar citas, herramientas, borrador y condición de plazo antes de la exposición. La ejecución final se verificó con la clave del grupo desde Colab; sus resultados están en `docs/evidencias/ejecuciones/`.

## Colab

Hay dos notebooks equivalentes:

- `AsistenteReg_EP2_Colab_GitHub.ipynb` (recomendado, usado en la evidencia final): la primera celda descarga el proyecto desde este repositorio en un commit fijo y muestra la versión utilizada. No requiere subir archivos.
- `AsistenteReg_EP2_OpenRouter.ipynb`: alternativa sin GitHub. La primera celda abre el selector de archivos para subir el ZIP del proyecto sin descomprimirlo; **Preparar proyecto** lo extrae y valida.

Las explicaciones técnicas se encuentran al final de cada notebook.

Continuar las celdas en orden. La instalación y las pruebas no consumen saldo; la preparación de embeddings y las consultas reales sí usan la clave de OpenRouter.

Después de configurar los secretos, la celda **Demostración de memoria en Neon sin consumir la API** utiliza la base PostgreSQL del grupo para verificar cinco intercambios, diez mensajes y la eliminación del más antiguo. Crea una conversación temporal y la elimina al terminar. Las pruebas automáticas sin conexión siguen usando bases SQLite temporales; esta demostración utiliza Neon.

En Secretos de Colab configurar `OPENROUTER_API_KEY` y `DATABASE_URL`, con acceso al cuaderno activado. El historial, borradores, consumo y caché permanecen en PostgreSQL aunque se elimine el entorno de Colab. La carpeta `runtime` sólo contiene la copia local del índice vectorial. Ver `docs/postgresql.md` para conectar y verificar la base.

## Estructura

```text
app.py
iniciar.bat
preparar_git_v2.bat
PUBLICAR_GITHUB.md
requirements.txt
.env.example
AsistenteReg_EP2_Colab_GitHub.ipynb
AsistenteReg_EP2_OpenRouter.ipynb
entrega/
  Informe_AsistenteReg_EP2.docx
  Presentacion_AsistenteReg_EP2.pptx
src/
  agent.py
  provider.py
  retrieval.py
  long_term.py
  storage.py
  ingest.py
  lexical.py
  guardrails.py
data/interna/
scripts/probar_openrouter.py
scripts/probar_base_datos.py
scripts/exportar_evidencias.py
tests/
docs/
  arquitectura.md
  arquitectura.png
  demo_y_defensa.md
  cobertura_pauta.md
  pendientes_del_equipo.md
  bocetos/
  evidencias/
```

`provider.py` es la única integración de modelos. `agent.py` construye el grafo. `retrieval.py` combina BM25 y similitud de vectores recibidos de OpenRouter mediante RRF. `storage.py` persiste historial, memoria, caché, borradores, trazas y consumo o reservas.

## Flujo y herramientas

1. Anonimizar formatos conocidos de datos personales y filtrar el alcance académico.
2. Cargar la ventana de `ConversationBufferWindowMemory` desde PostgreSQL: hasta 10 mensajes por conversación.
3. Preparar un plan que prioriza evidencia, plazo y escritura solicitada.
4. El modelo recibe los esquemas JSON de las tools y propone una llamada. El registro local valida y ejecuta la función.
5. El resultado vuelve al modelo, que elige el siguiente paso o responde.
6. Verificar citas y persistir historial y traza.

| Tool | Función | Controles |
|---|---|---|
| buscar_normativa | Consulta híbrida sobre el corpus | Hasta tres fragmentos completos con cita de documento, sección y versión. |
| evaluar_plazo | Compara la fecha del escenario con el calendario sintético | Retiro, suspensión o convalidación. Detecta plazo vencido y calendario inaplicable. |
| recuperar_borradores | Memoria semántica de artefactos guardados en Neon | Sólo a petición; misma conversación; hasta dos entre los veinte últimos; no recupera chat eliminado. |
| guardar_borrador | Guarda título y cuerpo en PostgreSQL | Requiere escritura solicitada en el turno, norma consultada, plazo y citas. Idempotente dentro de una solicitud. Nunca envía ni aprueba trámites. |

El plan inicial es determinista. La secuencia posterior depende de las observaciones de las tools y de la decisión del LLM, con máximo cuatro llamadas de chat y seis ejecuciones de herramientas por turno. Las solicitudes de embeddings se contabilizan aparte y comparten el mismo límite monetario.

## Memoria y contexto

El agente es **stateful**. Utiliza la clase real `ConversationBufferWindowMemory` de `langchain_classic.memory`, con `k=5`, `return_messages=True` y un adaptador `BaseChatMessageHistory` conectado a PostgreSQL. Cada intercambio contiene dos mensajes (pregunta y respuesta final): **5 intercambios equivalen a 10 mensajes**. El sistema, las llamadas a herramientas y sus observaciones pertenecen al turno en ejecución y no cuentan en esta ventana persistente.

`save_context` guarda cada intercambio en la tabla `asistentereg.turns` de PostgreSQL. En esa misma transacción, un `DELETE` elimina las filas anteriores a los últimos 5 intercambios de esa conversación. `load_memory_variables` reconstruye los mensajes que se envían al modelo. Al completar el intercambio 6 se conservan los intercambios 2 a 6: quedan 10 mensajes y los dos primeros se eliminan de la base.

Las trazas también se limitan a las últimas 5 por conversación. No hay resumen ni recuperación semántica del historial eliminado. La memoria de largo plazo conserva artefactos: `recuperar_borradores` busca con embeddings de OpenRouter hasta dos resultados entre los veinte borradores más recientes de esa conversación, con umbral 0,38. Los borradores sobreviven al borrado de los turnos y al reinicio. Se recuperan sólo cuando el usuario lo solicita, sin crearlos de nuevo ni atribuirles autoridad normativa. Usa `src/long_term.py` y la caché de embeddings de PostgreSQL; puede consumir saldo para vectores aún no cacheados.

Las conversaciones se aíslan por ID; repetir un perfil en otra conversación no recupera el historial anterior. Los borradores y la contabilidad se conservan por separado.

La clase se importa desde `langchain-classic`, fijado en dependencias para reproducir el mecanismo visto en clases. La memoria aporta continuidad y no sustituye la normativa. La recuperación semántica se usa para buscar documentos del corpus, con un umbral inicial de 0,38 que debe calibrarse con el modelo remoto.

`embedding_cache` en PostgreSQL reutiliza vectores por modelo y SHA-256 del texto anonimizado. `runtime/corpus_vectors.json` conserva una copia del índice y cambia al modificarse texto o modelo. Conservar el registro de consumo en la misma base durante los ensayos. Si se cambia el modelo de embeddings, sus vectores se regeneran.

Se limita cada petición de chat a 24.000 bytes UTF-8 de mensajes y esquemas. Si hace falta, se omiten de esa petición los intercambios históricos más antiguos, siempre completos; la base sigue conservando hasta 10 mensajes. Se mantienen la consulta actual y las llamadas a herramientas con sus resultados. Si eso solo supera la cota, se detiene el envío. Esta cota no es la ventana máxima del modelo. No se usa un checkpointer de LangGraph: una interrupción a mitad de turno no se reanuda automáticamente.

## Presupuesto de 1 USD

La variable `LOCAL_BUDGET_USD=0.75` limita el total de chat y embeddings del proyecto conectado a la misma base PostgreSQL, con margen respecto del dólar asignado. Las reservas se serializan entre equipos mediante bloqueos transaccionales. No conoce usos externos de la clave ni sustituye el saldo real de OpenRouter.

Cada petición reserva antes de enviarse una cota conservadora según las tarifas de los catálogos públicos de OpenRouter. Si el proveedor entrega `usage.cost`, se ajusta al coste reportado. Si hay un error o el coste no está disponible, se mantiene la reserva. El SDK no reintenta automáticamente. La caché evita pagar de nuevo por un texto idéntico.

En el primer inicio, la clave debe permitir el modelo de chat y el modelo de embeddings. Si un permiso o saldo falla, se informa el error: no se cambia a otro modelo ni se ejecuta uno local. Los datos enviados a embeddings pasan primero por el anonimizado de formatos conocidos.

Si aparece `NotFoundError` / 404, consultar `docs/solucion_openrouter_404.md`. La petición de chat mantiene `effort=low` y el soporte estricto de parámetros; omite `parallel_tool_calls`, que no figura entre los parámetros anunciados por los endpoints de Luna. La traza incluye el estado HTTP y el mensaje saneado del proveedor para distinguir routing, permisos y configuración.

## Demo y defensa

Los cuatro archivos de `data/interna` se conservaron byte a byte respecto de la primera entrega. La comparación y sus hashes están en `docs/evidencias/manual_ep1_verificado.json`. El notebook muestra los documentos indexados y el número de fragmentos. `runtime/corpus_manifest.json` registra archivos, hashes, configuración 700/120 y modelo de embeddings, y la traza de producción incluye esos datos en `rag`.

La respuesta final debe tener citas válidas. Si el LLM cierra sin una cita correcta después de guardar un borrador validado del turno, el sistema descarta ese cierre y reconstruye una respuesta con el plazo verificado y un extracto literal del manual. No anexa citas a afirmaciones inválidas ni utiliza borradores anteriores. La traza conserva `citas_validas_llm` y `validacion_final` para explicar la decisión. Sin esas evidencias, mantiene la abstención.

Ver `docs/demo_y_defensa.md`. En fecha simulada **2026-04-06**, preguntar:

> ¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta con los requisitos.

Mostrar la cita, la traza y el borrador. Cambiar al **2026-04-11** y preguntar si aún puede retirar: la herramienta debe mostrar `vencido`. Usar el mismo ID tras reiniciar para mostrar historial, y comprobar que una conversación nueva empieza con la memoria vacía.

## Validación disponible

La suite actual contiene 73 pruebas sin conexión y 5 de PostgreSQL. La versión final aprobó las 73 sin conexión; las cinco de PostgreSQL se omitieron porque no se configuró `TEST_DATABASE_URL` en esa ejecución. Se reprodujo el caso de tres llamadas simuladas con borrador válido y cierre del modelo sin citas, además de citas inventadas, calendario no aplicable y plazo vencido. Las 78 aprobaron también con PGlite; la ejecución queda en `docs/evidencias/salida_pruebas_postgresql.txt`; usa PostgreSQL embebido y SDK de IA simulado. La creación de las tablas, persistencia y retención se verificaron también por SQL en Neon; la conexión del driver desde Colab requiere ejecutar la celda correspondiente. Estas pruebas no verifican la calidad de la inferencia real con la clave del grupo. Esa verificación se hizo en Colab: 73 pruebas aprobadas y 5 omitidas (`salida_pruebas_colab.txt`), memoria k=5 en Neon (`prueba_base_datos.json`) y consultas reales en `ejecuciones/`, incluida una respuesta de convalidación con cita literal validada y abstenciones correctas fuera del manual.

## Extensión

Agregar una tool: definir una función tipada con `@tool`, incluirla en `Agent.tools` y probar sus resultados, errores y permisos. El esquema se genera con `convert_to_openai_tool`.

Para exponer herramientas aparte: sustituir sus implementaciones por adaptadores HTTP o clientes MCP con contrato JSON, autenticación, autorización, timeout e idempotencia. El servidor remoto no forma parte de esta entrega. La clave de OpenRouter permanece en el agente.

## Entrega y límites

El informe tiene un máximo de cinco páginas. La presentación sigue el aviso reciente: cinco minutos más dos de preguntas. El informe y la presentación finales están en `entrega/`.

El prototipo comparte la base entre los equipos del grupo y no implementa autenticación de usuarios. La conexión remota exige TLS y las credenciales se leen desde secretos. Los IDs separan contextos y no acreditan identidad. El filtro de alcance es léxico y la anonimización no detecta nombres ni todos los formatos: utilizar datos sintéticos. Las citas comprueban trazabilidad formal, no que cada frase se derive semánticamente de la fuente.

## Referencias

LangChain. (s. f.). Graph API overview. https://docs.langchain.com/oss/python/langgraph/graph-api

LangChain. (s. f.). Memory. https://docs.langchain.com/oss/python/concepts/memory

OpenRouter. (s. f.). Client tools. https://openrouter.ai/docs/guides/features/tool-calling

OpenRouter. (s. f.). Submit an embedding request. https://openrouter.ai/docs/api/api-reference/embeddings/submit-an-embedding-request

OpenRouter. (s. f.). Reasoning tokens. https://openrouter.ai/docs/guides/best-practices/reasoning-tokens

## Repositorio de entrega versión 2

Repositorio: https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2

Para publicar cambios, abrir `preparar_git_v2.bat` para configurar origin, preparar la rama main y crear el commit local. El preparador no hace push. Cuando indique LISTO, abrir CMD en esa carpeta y ejecutar `git push -u origin main`. Las instrucciones completas y la configuración de identidad están en [PUBLICAR_GITHUB.md](PUBLICAR_GITHUB.md).

La aplicación exige `DATABASE_URL`: no cambia automáticamente a SQLite ante un error. SQLite sólo se activa mediante una ruta explícita en las pruebas.

## Evidencia para la entrega

El notebook guarda cada ensayo por separado, incluidos errores, y permite descargar **Evidencias_AsistenteReg_EP2.zip** en la celda «Descargar evidencia», sin llamadas a modelos. Incluye los JSON de consultas, la prueba de Neon, el manifiesto del manual y las pruebas de Colab que se hayan ejecutado. La presencia de un archivo no equivale a aprobación: revisar resultados y citas. Copiar su carpeta `docs/evidencias` al repositorio tras revisar que las consultas sólo contienen datos sintéticos.

En ejecución local: `python scripts/exportar_evidencias.py`. Exporta únicamente archivos de evidencia aprobados y omite `.env` y credenciales conocidas. No descarga automáticamente datos desde Neon ni consume la API.

Bocetos de diseño: `docs/bocetos/README.md`. Pasos personales y de entrega: `docs/pendientes_del_equipo.md`.
