# Publicar AsistenteReg EP2 versión 2

Repositorio de esta entrega: https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2

Carpeta de trabajo indicada por Martín:

```text
C:\Users\elmar\Desktop\PRUEBA_SOL_IA\AsistenteReg_EP2_OpenRouter
```

## Colocar los archivos

Descomprimir el ZIP actualizado y copiar su contenido directamente en esa carpeta. Esta versión del ZIP no incluye una carpeta intermedia. Al abrir la ruta deben aparecer app.py, README.md, src, tests, docs, entrega y preparar_git_v2.bat.

Conservar .git si ya existe y el archivo privado .env. Los secretos de Colab permanecen configurados allí; no se incluyen en el ZIP. Los archivos antiguos dentro de una subcarpeta rag_registro no pertenecen a la nueva raíz: si existe esa copia anterior, moverla fuera de esta carpeta antes de preparar el commit.

## Preparar el commit sin publicar

Abrir preparar_git_v2.bat. El archivo trabaja en su propia carpeta, inicializa Git si hace falta, configura origin con el repositorio v2, utiliza la rama main y crea un commit con los cambios. No envía archivos a GitHub ni hace llamadas a OpenRouter.

Si Git pide nombre y correo, abrir CMD en la carpeta y configurar la identidad local, reemplazando los ejemplos por los datos de la cuenta:

```bat
git config user.name "Tu nombre"
git config user.email "Tu correo verificado o noreply de GitHub"
```

Después ejecutar de nuevo preparar_git_v2.bat. Un commit no requiere la API key del profesor ni DATABASE_URL.

## Hacer el push

Cuando el preparador indique LISTO, abrir CMD y ejecutar:

```bat
cd /d "C:\Users\elmar\Desktop\PRUEBA_SOL_IA\AsistenteReg_EP2_OpenRouter"
git push -u origin main
```

Completar la autenticación de GitHub si se solicita. Luego abrir el repositorio v2 y comprobar README, código, notebook, bocetos y entrega. En el momento de la preparación el repositorio remoto estaba vacío; si aparecen commits nuevos y Git rechaza el push, revisar ese mensaje antes de continuar. No usar force push.

Para iniciar la aplicación de Windows se usa iniciar.bat. Para la demostración en Colab se sube AsistenteReg_EP2_OpenRouter.ipynb y se carga el ZIP actualizado. El preparador de Git y el arranque de la aplicación son pasos independientes.
