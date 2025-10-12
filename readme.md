
---

# Django Auth API Project

A Django project with JWT authentication, REST API support, CORS handling, Redis caching, and Twilio integration for sending messages.

## Features

* Custom user model
* JWT authentication using **SimpleJWT**
* CORS and CSRF handling
* Redis caching support
* Twilio SMS integration
* Rate limiting using `django-ratelimit`
* Swagger API documentation using `drf-yasg`

---

##  Running the System

### Running Celery

* ``` celery -A core worker --beat --scheduler django --loglevel=info --pool=solo ```


### Option 1: Manual Start (Development)

* Terminal 1 - Run Django with Daphne:
```daphne -b 0.0.0.0 -p 8000 core.asgi:application```

* Terminal 2 - Start MQTT Client:
```python manage.py start_mqtt```

### Option 2: Auto-Start (Production-like)
The MQTT client auto-starts when Django runs (configured in apps.py).
bashdaphne -b 0.0.0.0 -p 8000 core.asgi:application

---

## Requirements

* Python 3.10+
* Django 4+
* Redis server 
* Twilio account 

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/kartik3165/BE-Project-backend.git
```

2. **Create and activate a virtual environment**

```bash
python -m venv env
source env/bin/activate   # Linux / macOS
env\Scripts\activate      # Windows
```

3. **Install dependencies**

```bash
pip install --upgrade pip
pip install django
pip install djangorestframework
pip install djangorestframework-simplejwt
pip install python-decouple
pip install django-cors-headers
pip install django-ratelimit
pip install drf-yasg
pip install django-redis
pip install twilio
```

4. **Set up environment variables**

Create a `.env` file in your project root:

```env
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# JWT Settings
ACCESS_TOKEN_LIFETIME_MINUTES=5
REFRESH_TOKEN_LIFETIME_DAYS=7
ROTATE_REFRESH_TOKENS=True
BLACKLIST_AFTER_ROTATION=True
UPDATE_LAST_LOGIN=True
JWT_ALGORITHM=HS256
JWT_AUTH_HEADER_TYPE=Bearer

# Database (PostgreSQL optional)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

> Note: Default database is SQLite. Uncomment PostgreSQL settings in `settings.py` if using PostgreSQL.

5. **Run migrations**

```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**

```bash
python manage.py createsuperuser
```

7. **Run the server**

```bash
python manage.py runserver
```

Access the API at `http://127.0.0.1:8000/`.

---

## Available Apps

* `auth_app`: Custom user model and authentication endpoints
* `admin`: Django admin panel
* `rest_framework`: API framework

---

## API Documentation

Swagger documentation is available if `drf-yasg` is installed:

```
http://127.0.0.1:8000/swagger/
```

---

## Notes

* CSRF middleware is disabled in settings for easier API testing. Enable it in production.
* Redis caching is optional but recommended for production.
* Twilio integration allows sending SMS messages via your Twilio account.

---


# .env File Config
```
SECRET_KEY='django-insecure-(*e#h@7-6!q$7vyj!zm&1ahu)fx^(q1dot(=p)qfvfk2&&7s#)'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=core_auth_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Redis URL
REDIS_URL=redis://127.0.0.1:6379/0

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000

# CSRF & Session Security

# Email Settings (Gmail Example)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=youremail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# HTTPS Settings
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False

CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False 
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_SAMESITE = 'Lax'

ACCESS_TOKEN_LIFETIME_MINUTES=5
REFRESH_TOKEN_LIFETIME_DAYS=7
ROTATE_REFRESH_TOKENS=True
BLACKLIST_AFTER_ROTATION=True
UPDATE_LAST_LOGIN=True

JWT_ALGORITHM=HS256
JWT_AUTH_HEADER_TYPE=Bearer

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

```
