"""Bocetos de precisión en SVG. Son diseños, no capturas de pruebas reales."""
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/bocetos';OUT.mkdir(parents=True,exist_ok=True)

def boceto(nombre,titulo,bloques):
 elementos=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="900" viewBox="0 0 1280 900">',
 '<rect width="1280" height="900" fill="#fafbfc"/>',
 '<style>text{font-family:DejaVu Sans,sans-serif;fill:#193348} .h{font-size:34px;font-weight:bold}.b{font-size:23px}.s{font-size:19px;fill:#4c6273}</style>',
 f'<text x="55" y="65" class="h">{escape(titulo)}</text>',
 '<text x="55" y="105" class="s">BOCETO DE DISEÑO · No corresponde a una captura de ejecución</text>']
 for x,y,w,h,titulo,lineas in bloques:
  elementos.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="white" stroke="#9cafbc" stroke-width="2"/>')
  elementos.append(f'<text x="{x+23}" y="{y+38}" class="b" font-weight="bold">{escape(titulo)}</text>')
  for j,linea in enumerate(lineas):
   elementos.append(f'<text x="{x+23}" y="{y+77+j*32}" class="s">{escape(linea)}</text>')
 elementos.append('<text x="55" y="862" class="s">AsistenteReg EP2 · OpenRouter para modelos · Neon para persistencia</text></svg>')
 (OUT/(nombre+'.svg')).write_text('\n'.join(elementos),encoding='utf-8')

boceto('01_preparacion','Preparación en Google Colab',[
 (55,145,1170,145,'1 Subir el proyecto ZIP',['from google.colab import files','archivos = files.upload()']),
 (55,315,555,205,'2 Preparar e instalar',['Extraer y validar el proyecto.','Ejecutar pruebas sin usar la API.','Guardar la salida para la entrega.']),
 (640,315,585,205,'3 Configurar secretos',['OPENROUTER_API_KEY   [oculto]','DATABASE_URL                [oculto]','No mostrar valores en el notebook.']),
 (55,545,1170,245,'4 Verificar Neon e indexar el manual',['Memoria: k=5, diez mensajes, eliminación del intercambio antiguo.','Cuatro archivos originales. Chunking de 700 caracteres con solapamiento 120.','17 fragmentos. Embeddings por OpenRouter, con caché en PostgreSQL.','Sólo los embeddings nuevos y las consultas reales consumen API.'])])
boceto('02_consulta','Consulta con respuesta y borrador',[
 (55,145,1170,145,'Perfil / Conversación / Fecha simulada',['grupo-ep2 / demo-openrouter / 2026-04-06','¿Hasta cuándo puedo retirar una asignatura? Prepara un borrador de consulta.']),
 (55,315,710,230,'Respuesta con fuente',['Plazo y requisitos tomados del manual.','[Documento, sección, versión]','La validación distingue el cierre del modelo','de una respuesta reconstruida desde evidencia.']),
 (795,315,430,230,'Traza de herramientas',['buscar_normativa','evaluar_plazo','guardar_borrador','Coste y estado de validación']),
 (55,570,710,220,'Borrador para revisión',['Título y texto persistidos en Neon.','No acredita aprobación. No enviado.','Recuperable en la misma conversación.']),
 (795,570,430,220,'Continuidad y evidencia',['Historial: hasta diez mensajes.','Memoria duradera: borradores.','Exportar ensayos a ZIP.'])])
boceto('03_estados','Estados y decisiones observables',[
 (55,145,555,230,'Plazo vigente',['Fecha de demo: 2026-04-06.','Consultar requisitos y calendario.','Permitir borrador solicitado con citas.','Comprobar herramientas en la traza.']),
 (640,145,585,230,'Plazo vencido',['Fecha de demo: 2026-04-11.','Informar el vencimiento y derivar.','Etiquetar borrador de orientación.','No afirmar aceptación del trámite.']),
 (55,405,555,210,'Sin respaldo o fallo de API',['Abstención si no hay evidencia.','Error saneado en la traza.','Cero reintentos automáticos.']),
 (640,405,585,210,'Recuperar un borrador',['Sólo cuando el usuario lo pide.','Hasta dos resultados de veinte recientes.','Referencia BORRADOR, sin autoridad normativa.']),
 (55,645,1170,145,'Evidencia para revisar',['Cada ejecución guarda su propio JSON, incluso si falla.','Descargar evidencia no realiza llamadas a modelos. Revisar antes de publicar.'])])
(OUT/'README.md').write_text('''# Bocetos de diseño EP2\n\nEstos tres bocetos describen la preparación, consulta y estados de la interfaz Colab. Son diagramas de diseño y no capturas reales ni evidencia de inferencia. Las versiones SVG son editables y las PNG facilitan la vista en GitHub.\n\n- 01_preparacion: subida de ZIP, secretos, prueba de Neon e indexación.\n- 02_consulta: respuesta, traza, borrador, memoria y exportación.\n- 03_estados: vigente, vencido, fallo, abstención y recuperación de artefactos.\n\nGenerar SVG: `python scripts/generar_bocetos.py`. La evidencia real se exporta desde el notebook; debe añadirse a docs/evidencias después de ejecutar los ensayos.\n''',encoding='utf-8')
