import os
import datetime
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'yn0@+&mjcn7jic#)^ijx-)cijo&v8+pn1z-b+1(kwxadk_f*y*')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('ENVDEBUG', cast=bool, default=True)


ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'sireedu-server-acb1c893f21b.herokuapp.com']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sisen.survey.apps.SurveyConfig',
    'rest_framework',
    'corsheaders',
    'django_rest_passwordreset',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sisen.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates/'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sisen.wsgi.application'

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#    }
# }

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql',
#        'NAME': config('NAME'),
#        'USER': config('USER'),
#        'PASSWORD': config('PASSWORD'),
#        'HOST': config('HOST'),
#        'PORT': '5432',
#    }
# }

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql',
#        'NAME': "d16eu17jts3ojv",
#        'USER': "u74lkilpdkp2m0",
#        'PASSWORD': "p5cdebd0132f659b05404ee044e64904b9d1b366b0b06f27113e7c47391868088",
#        'HOST': "cat670aihdrkt1.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
#        'PORT': '5432',
#    }
# }

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
    )
}
    

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'assets'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

#STATICFILES_DIRS = os.path.join(BASE_DIR, "staticfiles")

# CLIENT_RESET_PASSWORD_CONFIRMATION_URL = 'http://localhost:8080/#/password-reset-confirmation'
CLIENT_RESET_PASSWORD_CONFIRMATION_URL = config('CLIENT_RESET_PASSWORD_CONFIRMATION')

# CLIENT_EMAIL_VERIFICATION_URL = 'http://localhost:3000/welcome'
CLIENT_EMAIL_VERIFICATION_URL = config('CLIENT_EMAIL_VERIFICATION_URL')

DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME = 2 #hours
DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE = True

REST_FRAMEWORK = {
    # Disables Browsable API in production
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
}

# Remove config or increase interval when in production
JWT_AUTH = {
    'JWT_ALLOW_REFRESH': True,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_EXPIRATION_DELTA': datetime.timedelta(minutes=30),
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'sisen.survey.utils.jwt_response_payload_handler',
}

CORS_ORIGIN_WHITELIST = [
    'http://localhost:8080',
    'https://sireedu.com.br',
    'https://www.sireedu.com.br',
    'https://sisen-client-sire-edus-projects.vercel.app',
    'http://localhost:3000',
    'https://react-sire-client.vercel.app',
    'https://sire-client-three.vercel.app',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
