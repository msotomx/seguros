@echo off
cd /d C:\Users\msoto\Documents\BITSISTEMAS\PROYECTOS\seguros
call venv\Scripts\activate.bat
python manage.py marcar_polizas_vencidas --log-events >> logs\marcar_polizas_vencidas.log 2>&1
