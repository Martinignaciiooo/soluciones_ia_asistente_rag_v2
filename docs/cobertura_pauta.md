# Correspondencia con la pauta EP2

Estado de preparación, no calificación. El criterio de aceptación final corresponde al docente. Las secciones argumentativas y personales deben completarse por el equipo sin IA.

| Indicador | Implementación y evidencia incluida | Paso final del equipo |
|---|---|---|
| IE1 Herramientas autónomas | buscar_normativa, evaluar_plazo, guardar_borrador y recuperar_borradores; contratos y errores probados | Ejecutar y exportar traza real de esta versión |
| IE2 Frameworks | LangGraph, herramientas tipadas LangChain y SDK OpenAI compatible con OpenRouter | Defender las elecciones con razones propias |
| IE3 Memoria | ConversationBufferWindowMemory k=5; PostgreSQL borra intercambios anteriores; memoria duradera de borradores | Ejecutar verificación Neon y continuidad en Colab |
| IE4 Recuperación semántica | RAG del manual y búsqueda de borradores persistidos mediante embeddings OpenRouter y umbral 0,38 | Comprobar pertinencia y calibrar con ejemplos reales |
| IE5 Planificación | Plan inicial, ciclo tools/observaciones, límites y decisiones por plazo | Revisar adaptación real ante fecha vigente y vencida |
| IE6 Informe técnico | Informe editable de cinco páginas, arquitectura, flujo, documentación y pruebas | Revisar y completar secciones propias |
| IE7 Adaptación demostrada | Tests de vigente/vencido/calendario inaplicable, evidencia insuficiente y recuperación de artefactos | Demo real ensayada y evidencia exportada |
| IE8 Repositorio y diagramas | README, diagrama, bocetos y scripts en la raíz del proyecto | Publicar y verificar URL de GitHub |
| IE9 Justificación | Componentes, contratos y referencias documentados; espacios reservados | Redactar justificaciones sin IA |
| IE10 Comunicación | PPT con cinco láminas principales y anexo; guía cinco minutos más dos de preguntas | Completar aprendizajes y practicar ambos |

## Evidencia y alcance

La suite contiene 73 pruebas sin IA y cinco pruebas PostgreSQL. La ejecución normal guarda su salida en salida_pruebas.txt; si no hay TEST_DATABASE_URL, las cinco PostgreSQL se omiten. Las 78 aprobaron con PostgreSQL embebido; esa ejecución se registra en salida_pruebas_postgresql.txt. No equivale a disponibilidad o rendimiento de Neon.

La configuración de tablas y retención se verificó por SQL en Neon (prueba_neon_real.json). El usuario aportó una traza real de OpenRouter con tres llamadas y borrador guardado, pero el cierre falló por validación de citas. La corrección tiene regresiones sin IA; falta exportar un ensayo real corregido desde Colab. No confundir esa traza anterior con aprobación de esta versión.

La memoria de largo plazo implementada es de artefactos, no un archivo indefinido del chat. Los borradores permanecen al borrar la ventana y se recuperan sólo a petición y en el mismo ID. La prueba test_long_term.py verifica reinicio, aislamiento, umbral y lectura acotada.

Los bocetos de docs/bocetos son diseños de interfaz, no capturas de ejecuciones. El checklist completo está en pendientes_del_equipo.md.

Repositorio v2 de entrega: https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2. El push lo realiza el equipo mediante PUBLICAR_GITHUB.md.
