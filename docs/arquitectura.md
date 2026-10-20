# Arquitectura con OpenRouter

```mermaid
flowchart TD
 U["Consulta del estudiante"] --> P["Preparar entrada y plan"]
 P -->|"Fuera de alcance"| V["Validar y persistir"]
 P --> M["GPT Luna mediante OpenRouter"]
 M -->|"Propone tool"| T["Registro de herramientas"]
 T --> R["Buscar normativa"]
 T --> C["Evaluar plazo"]
 T --> B["Guardar borrador"]
 T --> L["Recuperar borradores persistidos"]
 L --> O
 D --> L
 E --> L
 R --> O["Observar resultados"]
 C --> O
 B --> O
 O --> M
 M -->|"Respuesta o límite"| V
 D[("PostgreSQL y caché")] <--> P
 D <--> V
 B --> D
 E["Embeddings mediante OpenRouter"] --> R
 V --> S["Respuesta con citas o derivación"]
```

Sólo `src/provider.py` se conecta a modelos. Chat y embeddings usan la misma API y comparten el tope monetario. No se ejecutan modelos en el equipo. Las búsquedas del manual y de borradores pueden solicitar embeddings remotos. LangGraph controla las transiciones. `ConversationBufferWindowMemory(k=5)` usa un adaptador PostgreSQL para conservar hasta 10 mensajes por conversación y borrar los anteriores. El agente es stateful; cada solicitud al modelo incluye explícitamente el contexto seleccionado.

La memoria de corto plazo elimina turnos antiguos. La de largo plazo recupera artefactos guardados mediante `recuperar_borradores`, sólo a petición, con vectores de OpenRouter y datos de la misma conversación. Consulta hasta veinte borradores, devuelve hasta dos y no atribuye a esos textos vigencia normativa. `src/long_term.py` aplica la similitud y el umbral.
