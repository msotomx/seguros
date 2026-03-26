@echo off
cd /d C:\Users\msoto\Documents\BITSISTEMAS\PROYECTOS\seguros
call venv\Scripts\activate.bat
python manage.py marcar_pagos_vencidos --log-events >> logs\marcar_pagos_vencidos.log 2>&1
