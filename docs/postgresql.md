# Conectar la base PostgreSQL

## Base del grupo ya creada

El proyecto [asistentereg-ep2](https://console.neon.tech/app/projects/rapid-tooth-70776957) contiene la base `asistentereg`, la rama `main` y las cinco tablas del esquema `asistentereg`. Se creó en el plan gratuito, en São Paulo, con un compute de 0,25 CU.

En **Connect**, seleccionar la base `asistentereg` y el rol `asistentereg_owner`, copiar la cadena PostgreSQL y guardarla en el secreto `DATABASE_URL` de Colab. Las credenciales no se incluyen en esta entrega.

La escritura, la persistencia y la retención de cinco intercambios se comprobaron mediante SQL en Neon, sin llamadas a OpenRouter. Los registros de prueba se eliminaron. La evidencia está en `docs/evidencias/prueba_neon_real.json`. La comprobación del driver y de la clase de memoria contra esta base se debe ejecutar con la celda `verificar_base(store)` en Colab: el entorno de preparación no resuelve por DNS el host de Neon.

## Configuración general

1. Crear un proyecto y una base en Neon. También se puede usar PostgreSQL de Supabase.
2. Copiar la cadena de conexión desde **Connect**. Usar la URL completa que comienza por `postgresql://`, sin `psql` ni comillas. Mantener `sslmode=require` o la verificación de certificado.
3. En Secretos de Colab agregar `DATABASE_URL` con esa URL y `OPENROUTER_API_KEY` con la clave del grupo. Activar el acceso al cuaderno de ambos secretos. En Windows usar esas mismas variables en `.env`.
4. Ejecutar el notebook en orden. `Store()` abre PostgreSQL con psycopg y crea automáticamente el esquema `asistentereg` y sus tablas; no se necesita crear tablas manualmente.
5. Ejecutar la celda de verificación de base: comprueba persistencia y retención sin llamar a modelos. También se puede ejecutar `python scripts/probar_base_datos.py`.
6. Preparar los embeddings y consultar al agente. Estas etapas sí consumen el saldo de OpenRouter.

## Memoria y tablas

`ConversationBufferWindowMemory(k=5)` se conecta mediante `PersistentWindowHistory`. La tabla `asistentereg.turns` conserva hasta cinco intercambios por conversación, equivalentes a diez mensajes. Guardar y borrar los intercambios antiguos ocurre en una misma transacción con un bloqueo por conversación. Las trazas también conservan las cinco últimas por conversación.

`drafts` conserva borradores, `usage` registra consumo y reservas y `embedding_cache` reutiliza vectores. El control de presupuesto usa un bloqueo transaccional PostgreSQL compartido por los equipos conectados al mismo esquema. No contabiliza usos de la clave fuera de esta aplicación.

El historial y estos registros permanecen fuera de Colab. Reutilizar la misma URL y el mismo ID de conversación para recuperar la ventana después de reiniciar o desde otro computador. Una conversación nueva empieza sin historial. La clave y la URL no se imprimen ni se incluyen en el ZIP.

## Pruebas y conexión real

`python -m pytest tests -q` ejecuta las pruebas sin consumir modelos: utiliza SQLite temporal para los tests sin conexión. Las pruebas de PostgreSQL se omiten si no se configura `TEST_DATABASE_URL`. Esta variable es sólo para una base de pruebas; cada test crea y elimina un esquema propio.

La celda `verificar_base(store)` es la comprobación para la base del grupo. Crea una conversación temporal, guarda seis intercambios, verifica que sólo queden del segundo al sexto y elimina esa conversación temporal. No borra conversaciones ajenas, borradores ni consumo.

Si ya se usó una versión SQLite, sus datos no se copian automáticamente a la base nueva. Conservar el archivo anterior y revisar el saldo real de OpenRouter antes de continuar los ensayos.
