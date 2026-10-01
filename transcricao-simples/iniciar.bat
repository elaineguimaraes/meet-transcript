@echo off
rem Abre a interface grafica. A janela preta mostra erros, caso algo de errado.
cd /d "%~dp0"

set PY=py
where py >nul 2>nul || set PY=python

%PY% app.py || pause
