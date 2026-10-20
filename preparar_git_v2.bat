@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo No se encontro Git. Instala Git para Windows y vuelve a ejecutar este archivo.
  goto error
)
if not exist "app.py" (
  echo Coloca este archivo junto a app.py y README.md, en la raiz del proyecto.
  goto error
)
if not exist ".git" (
  git init -b main
  if errorlevel 1 goto error
)
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2.git
) else (
  git remote set-url origin https://github.com/Martinignaciiooo/soluciones_ia_asistente_rag_v2.git
)
if errorlevel 1 goto error
for /f "delims=" %%B in ('git symbolic-ref --quiet --short HEAD') do set "task_git_branch=%%B"
if not defined task_git_branch (
  echo El repositorio no esta en una rama. Revisa git status antes de continuar.
  goto error
)
if not "%task_git_branch%"=="main" (
  git branch -m main
  if errorlevel 1 goto error
)
git add -- .
if errorlevel 1 goto error
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Actualizar AsistenteReg EP2 con OpenRouter y Neon"
  if errorlevel 1 goto error
)
git remote -v
git status --short
echo.
echo LISTO. El proyecto esta preparado localmente. No se hizo push.
echo Abre CMD en esta carpeta y ejecuta:
echo git push -u origin main
pause
exit /b 0
:error
echo.
echo No se completo la preparacion. Revisa el mensaje anterior. No se hizo push.
echo Si Git solicita tu identidad, configura user.name y user.email segun PUBLICAR_GITHUB.md.
pause
exit /b 1
