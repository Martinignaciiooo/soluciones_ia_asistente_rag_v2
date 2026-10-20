# Guía de demo y defensa

## Cinco minutos de presentación

| Tiempo | Integrante sugerido | Contenido |
|---|---|---|
| 0:00–0:35 | Martín | Problema organizacional simulado y alcance de la solución. |
| 0:35–1:35 | Valentina | Arquitectura con OpenRouter para chat y embeddings. Tools y ciclo de observaciones. |
| 1:35–2:20 | Martín | ConversationBufferWindowMemory, estado persistente y eliminación de mensajes antiguos. |
| 2:20–4:20 | Ambos | Demo real de consulta, plazo y borrador. |
| 4:20–5:00 | Ambos | Conclusiones y aprendizajes redactados por ustedes sin IA. |

Después: dos minutos de preguntas, según el aviso reciente del profesor.

## Preparación

1. Instalar dependencias y ejecutar `python -m pytest tests -q`: pruebas sin red ni gasto de clave.
2. Configurar `OPENROUTER_API_KEY` y `DATABASE_URL` en `.env` o Secrets de Colab. Verificar PostgreSQL con la celda del notebook o `python scripts/probar_base_datos.py`, sin usar modelos. Nunca proyectar los secretos.
3. Ejecutar una prueba manual real con `python scripts/probar_openrouter.py`. Esta prueba sí consume chat y embeddings. La clave debe permitir ambos modelos configurados.
4. Revisar citas, herramientas, borrador y respuesta ante plazo vencido. Revisar saldo y usar un único equipo para presentar.
5. Completar justificaciones, conclusiones y reflexiones propias, datos de integrantes y repositorio actualizado.

## Demo breve

Fecha simulada **2026-04-06**. Preguntar:

> ¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta con los requisitos.

Mostrar respuesta con cita, traza de herramientas y borrador guardado en PostgreSQL. Aclarar que el sistema no envió ni aprobó un trámite. Cambiar a **2026-04-11** y preguntar **¿Todavía puedo retirar una asignatura?** La tool debe devolver vencido. Confirmar que la respuesta real se adapte antes de la presentación.

La memoria se demuestra reabriendo el mismo ID tras reiniciar la app. Otra conversación empieza con una ventana vacía. El notebook incluye una demostración de retención sin API: tras guardar 6 intercambios quedan 5 filas, equivalentes a 10 mensajes, y se elimina el primero. No usar la evidencia con SDK simulado como si fuera una inferencia real.

## Hechos del código para preparar las respuestas

**Selección de tools.** El LLM recibe nombre, descripción y JSON Schema. Devuelve `tool_calls`; el registro valida y ejecuta nombres conocidos. Los resultados vuelven al LLM como observaciones. El programa exige evidencia y plazo antes de escribir.

**Memoria de largo plazo.** La tool `recuperar_borradores` consulta semánticamente artefactos persistidos en Neon. Busca hasta dos entre los veinte últimos borradores de la misma conversación. Los vectores usan la API y su caché. No conserva ni reconstruye mensajes eliminados. Para mostrarla: «Recupera mi borrador anterior de retiro».

**Agregar una tool.** Función tipada `@tool` en `Agent.tools`, inclusión en la lista y pruebas de argumentos, resultados y permisos. El esquema se deriva con `convert_to_openai_tool`.

**Clase de memoria.** Se instancia `ConversationBufferWindowMemory` de `langchain_classic.memory`, con `k=5` y `return_messages=True`. Guarda y carga por medio de un adaptador PostgreSQL. Un intercambio contiene una pregunta y una respuesta: 5 intercambios son 10 mensajes.

**Retención y contexto.** Al guardar el intercambio 6 se eliminan de la tabla mediante DELETE los dos mensajes del primero. No se mantiene un resumen ni una memoria semántica de los mensajes borrados. La petición tiene una cota adicional de 24.000 bytes: puede omitir intercambios históricos completos para ajustarse, conservando el turno actual y sus herramientas. No confundir los 10 mensajes de retención con la capacidad máxima del modelo.

**Estado e historial.** El agente es stateful porque restaura su ventana desde PostgreSQL remoto, tabla `asistentereg.turns`, por ID de conversación. Las trazas se limitan también a las últimas 5 por conversación. Los borradores y la contabilidad permanecen aparte. Las llamadas al modelo incluyen el historial explícitamente. Reutilizar DATABASE_URL y el mismo ID permite recuperar la memoria desde otro entorno o equipo.

**Control de coste.** Chat y embeddings comparten el tope del proyecto de USD 0,75. Antes de cada petición se reserva un importe conservador. Si hay coste reportado se ajusta; si hay error, queda la reserva. La caché evita repetir solicitudes idénticas. Los equipos que usan esta misma base comparten el registro de consumo; los usos externos de la clave no se contabilizan.

**Planificación.** Plan inicial que prioriza contexto, norma, plazo y borrador solicitado. El modelo decide los pasos posteriores según observaciones. `evaluar_plazo` compara fechas por código y modifica la acción recomendada. Se permite abstención cuando falta evidencia.

**Fallo de API.** Mensaje controlado y cero reintentos del SDK. No existe una ruta de ejecución con otro proveedor o modelo en el equipo. El historial y los borradores ya persistidos permanecen.

**Servidor remoto de tools.** Adaptadores HTTP o MCP con contrato JSON, autenticación, autorización, timeout e idempotencia. El LLM permanece en OpenRouter y la clave se conserva en el agente. Esta ampliación es un diseño, no un servidor implementado.

**Citas.** Validación de documento, sección y versión exactamente recuperados. Las referencias BORRADOR identifican memoria de artefactos y no constituyen normativa. Si el cierre no cita bien tras guardar un borrador validado del turno, se reconstruye desde las fuentes y el plazo verificado sin otra llamada. Esto verifica trazabilidad formal y no prueba que cada frase esté respaldada semánticamente.

## Escritura propia

Redactar sin IA las razones de las decisiones de diseño, las conclusiones y la reflexión de cada integrante. Usar sólo experiencias, contribuciones y pruebas que el equipo pueda explicar y haya realizado. Los puntos anteriores son una descripción del código, no una justificación personal redactada por el equipo.

## Exportar ensayos

Ejecutar la celda «Descargar evidencia». Conserva cada consulta de esta sesión por separado, la comprobación de Neon, el manifiesto del manual y la salida de pruebas. Revisar errores y contenido antes de subir `docs/evidencias` a GitHub. Para la demo de cinco minutos usar una consulta principal; preparar los demás casos antes y mostrarlos sólo si alcanza el tiempo.
