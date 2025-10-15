#!/bin/bash
python manage.py collectstatic --link --noinput
python manage.py migrate 
exec uvicorn core.asgi:application --host 0.0.0.0 --port 8000