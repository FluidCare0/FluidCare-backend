uv run celery -A core worker --beat -l info -Q celery,high_priority
