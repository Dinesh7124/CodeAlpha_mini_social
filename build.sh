#!/usr/bin/env bash

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py autocreate_superuser

echo "✅ Build complete!"