# Evidencia del proyecto

Las pruebas automáticas usan proveedor simulado y no consumen la clave del profesor. La evidencia debe interpretarse por su tipo y versión.

| Archivo | Qué comprueba | Alcance |
|---|---|---|
| salida_pruebas_postgresql.txt | 78 pruebas aprobadas de la versión final | PostgreSQL embebido y SDK simulado |
| salida_pruebas.txt | 73 aprobadas y 5 omitidas | Sin TEST_DATABASE_URL no ejecuta los cinco tests de PostgreSQL |
| verificacion_entrega.json | Modelos, notebook, artefactos y hashes del manual | Revisión del paquete, sin inferencia real |
| manual_ep1_verificado.json | Manual original de la EP1 sin cambios y 17 fragmentos | Integridad y chunking |
| prueba_neon_real.json | Esquema y retención comprobados mediante SQL en Neon | No es una prueba del driver de Colab |
| postgresql_embebido.json | Celda de configuración y memoria con PostgreSQL embebido | Sin conexión a la base Neon del grupo ni IA |
| ejecuciones/*.json | Consultas que el equipo ejecute y exporte desde Colab | Revisar errores, respuesta, citas y llamadas en cada JSON |
| prueba_base_datos.json | Comprobación de la base usada por el equipo | Se genera al ejecutar la celda o script; no usa IA |

Los archivos correccion_routing_openrouter.json, manual_respuesta_regresion.json, flujos_simulados.json, entorno_limpio.txt e interfaz_local.txt conservan comprobaciones anteriores. Sus conteos pueden corresponder a una versión previa; para el total actual usar las dos salidas de pruebas de la tabla.

No se incluye un ensayo real aprobado de la corrección final: el equipo debe generarlo con su clave y la celda «Descargar evidencia». No sustituirlo por las regresiones simuladas.
