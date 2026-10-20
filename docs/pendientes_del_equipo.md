# Antes de entregar AsistenteReg EP2

El paquete incluye la implementación, notebook, pruebas, informe editable, PPT y bocetos. Este checklist separa los pasos que requieren la intervención del equipo. No declarar cumplimiento total hasta completarlos.

## Redacción y datos del equipo

- [ ] Completar el apellido de Valentina y revisar los datos de ambos integrantes.
- [ ] Redactar las justificaciones técnicas propias en el apartado 12 del informe. Describir las decisiones realmente comprendidas y evaluadas por el equipo.
- [ ] Escribir las conclusiones grupales y una reflexión personal de cada integrante, sin IA, como exige la pauta. Sustituir también la lámina 5 del PPT.
- [ ] Revisar la declaración de IA y las referencias. Mantener el informe en un máximo de cinco páginas después de editarlo.

## Verificación real en Colab

Descargar el notebook y el ZIP de esta misma versión. Abrir el notebook en Colab, subir el ZIP en la primera celda y ejecutar las celdas en orden. Configurar únicamente OPENROUTER_API_KEY y DATABASE_URL en Secretos con acceso al cuaderno. No mostrarlos en pantalla.

- [ ] Ejecutar la prueba de Neon: k=5, 10 mensajes, persistencia entre conexiones y borrado del intercambio más antiguo. No consume API.
- [ ] Indexar el manual: cuatro archivos originales, 17 fragmentos, 700 caracteres y solapamiento 120. Los embeddings nuevos consumen saldo.
- [ ] Fecha 2026-04-06: «¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta con los requisitos». Comprobar plazo 10-04-2026, mínimo 12 SCT, citas, borrador guardado y enviado=false.
- [ ] Misma conversación: «Recupera mi borrador anterior de retiro». Revisar tool recuperar_borradores y cita BORRADOR. Se consulta memoria duradera de artefactos y no se crea un borrador nuevo.
- [ ] Cambiar a 2026-04-11: «¿Todavía puedo retirar una asignatura?». Comprobar estado vencido y orientación, sin promesa de aceptación.
- [ ] Reabrir la misma conversación en un entorno nuevo y mostrar que persiste el historial. Usar otro ID y verificar que comienza vacío.
- [ ] Probar una consulta sin evidencia: el agente debe abstenerse. Revisar el resultado observado sin dar por aprobada una respuesta sólo porque contiene una cita.
- [ ] Ejecutar «Descargar evidencia» al final del notebook. Descomprimir el ZIP de evidencias y copiar su carpeta docs/evidencias a la raíz del proyecto. Revisar los JSON y retirar datos personales antes de publicarlos.

Cada consulta real puede consumir chat y embeddings. No repetir ensayos innecesarios. La exportación no llama a la API. Las pruebas automáticas simulan el proveedor; no demuestran precisión real del modelo.

## Publicación y entrega

- [ ] Copiar el ZIP actualizado, sin carpeta intermedia, a C:\Users\elmar\Desktop\PRUEBA_SOL_IA\AsistenteReg_EP2_OpenRouter. Preparar el commit con preparar_git_v2.bat y hacer push a https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2. Revisar PUBLICAR_GITHUB.md.
- [ ] Incluir README, src, tests, scripts, data, docs/bocetos, docs/evidencias, notebook e informe/PPT finales en entrega. Confirmar que el enlace abre sin depender de archivos de tu computador.
- [ ] Revisar que no se publicaron .env, claves, DATABASE_URL, salidas privadas ni cachés de ejecución. El paquete entregado no contiene esas credenciales.
- [ ] Ensayar cinco minutos entre ambos más dos de preguntas. Llevar una sesión lista y la evidencia previa como respaldo, identificándola como ejecución anterior.
- [ ] Enviar el informe y URL del repositorio por AVA y al correo del profesor dentro del plazo. Este paquete no hace esos envíos.

## Límites que deben explicar

La ventana conserva cinco intercambios; los anteriores se borran. La memoria de largo plazo conserva borradores de la misma conversación y recupera semánticamente hasta dos entre los veinte últimos. No recupera mensajes eliminados. El RAG del manual aporta conocimiento documental independiente. Los umbrales semánticos requieren calibración con ensayos reales. No se implementa autenticación de usuarios, aprobación de trámites ni un servidor remoto de tools.
