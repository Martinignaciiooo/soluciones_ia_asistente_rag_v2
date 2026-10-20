@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
findstr /r "^OPENROUTER_API_KEY=..*" .env >nul
if errorlevel 1 (
  echo Ingresa OPENROUTER_API_KEY y DATABASE_URL dentro de .env, guarda y cierra el bloc.
  notepad .env
  pause
)
findstr /r "^DATABASE_URL=..*" .env >nul
if errorlevel 1 (
  echo Ingresa la URL PostgreSQL de Neon o Supabase en DATABASE_URL, guarda y cierra el bloc.
  notepad .env
  pause
)
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
pause
exit /b 0
:error
echo Revisa el mensaje anterior. Se recomienda Python 3.11 o 3.12.
pause
exit /b 1
