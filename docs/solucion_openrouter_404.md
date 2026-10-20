# Corrección de routing de GPT Luna

El catálogo público de endpoints de `openai/gpt-6-luna` no anuncia `parallel_tool_calls`. La combinación anterior de ese parámetro con `provider.require_parameters=True` podía excluir los endpoints. El código corregido omite ese parámetro, mantiene `reasoning.effort=low`, `tools`, `tool_choice=auto` y el límite de salida. La ejecución de herramientas continúa en el bucle secuencial del agente.

Fuentes consultadas el 20 de octubre de 2026:

- https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints
- https://openrouter.ai/docs/guides/routing/provider-selection

## Corregir una sesión de Colab ya abierta

Ejecutar esta celda una vez antes de volver a pulsar **Consultar**. Ajusta el cliente ya creado y no envía ninguna petición a OpenRouter. La próxima consulta sí usa la API. El ZIP actual ya incorpora la corrección permanente.

```python
crear_original = provider.client.chat.completions.create
def crear_compatible(*args, _original=crear_original, **kwargs):
    kwargs.pop('parallel_tool_calls', None)
    return _original(*args, **kwargs)
provider.client.chat.completions.create = crear_compatible
print('Ajuste aplicado. Vuelve a pulsar Consultar.')
```

El error original sólo incluía la clase `NotFoundError`, por lo que no permite excluir otras causas de un 404, como una restricción de routing de la cuenta. La versión nueva añade estado HTTP, mensaje saneado del proveedor, modelo e intentos a la traza. No muestra requests, cabeceras ni credenciales. `llamadas` cuenta respuestas de chat recibidas; `intentos_llamada` registra intentos del agente.

El importe mostrado por el proyecto suma consumo reportado y reservas conservadoras. Si una petición falla, su reserva se mantiene; ese importe no acredita un cobro real de OpenRouter. No se eliminaron ni corrigieron registros monetarios existentes al aplicar este cambio.

La regresión se verificó con el SDK real y transporte HTTP simulado: 59 pruebas sin conexión aprobadas, 5 integraciones PostgreSQL omitidas en esta ejecución. No se usó la clave del grupo ni se hizo inferencia real para verificar este ajuste.
