@echo off
rem Instala as dependencias. Se encontrar uma GPU NVIDIA, instala tambem o suporte a CUDA.
cd /d "%~dp0"

set PY=py
where py >nul 2>nul || set PY=python

%PY% --version || (
    echo.
    echo Python nao encontrado. Instale o Python 3.9 a 3.13 em https://www.python.org/downloads/
    pause
    exit /b 1
)

%PY% -m pip install -r requirements.txt || goto erro

where nvidia-smi >nul 2>nul && (
    echo.
    echo GPU NVIDIA encontrada, instalando suporte a CUDA...
    %PY% -m pip install -r requirements-gpu.txt || goto erro
)

echo.
echo Pronto! Agora abra o iniciar.bat
pause
exit /b 0

:erro
echo.
echo A instalacao falhou. Veja a mensagem acima.
pause
exit /b 1
