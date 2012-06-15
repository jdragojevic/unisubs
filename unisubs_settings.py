# Amara, universalsubtitles.org
# 
# Copyright (C) 2012 Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see 
# http://www.gnu.org/licenses/agpl-3.0.html.

from datetime import timedelta
from settings import *
from server_local_settings import *


DEBUG = False

ADMINS = (
    ('Craig Zheng', 'craig@pculture.org'),
    ('universalsubtitles-errors', 'universalsubtitles-errors@pculture.org')
)

if INSTALLATION == DEV:
    SITE_ID = 13
    SITE_NAME = 'unisubsdev'
    REDIS_DB = "3"
    EMAIL_SUBJECT_PREFIX = '[usubs-dev]'
    SENTRY_TESTING = True
    SOLR_ROOT = '/usr/share/'
    BROKER_BACKEND = 'amqplib'
    BROKER_HOST = "localhost"
    BROKER_PORT = 5672
    BROKER_USER = "unisub"
    BROKER_PASSWORD = "unisub"
    BROKER_VHOST = "unisub"
    CELERY_TASK_RESULT_EXPIRES = timedelta(days=7)
elif INSTALLATION == STAGING:
    SITE_ID = 14
    SITE_NAME = 'unisubsstaging'
    REDIS_DB = "2"
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    EMAIL_SUBJECT_PREFIX = '[usubs-staging]'
    CELERY_TASK_RESULT_EXPIRES = timedelta(days=7)
elif INSTALLATION == PRODUCTION:
    SITE_ID = 8
    SITE_NAME = 'unisubs'
    REDIS_DB = "1"
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    EMAIL_SUBJECT_PREFIX = '[usubs-production]'
    COMPRESS_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    ADMINS = (
      ('universalsubtitles-errors', 'universalsubtitles-errors@pculture.org'),
    )
    # only send actual email on the production server
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    
if INSTALLATION == STAGING or INSTALLATION == PRODUCTION:
    DATABASE_ROUTERS = ['routers.UnisubsRouter']
    AWS_STORAGE_BUCKET_NAME = DEFAULT_BUCKET
    COMPRESS_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    COMPRESS_URL = STATIC_URL
    SOLR_ROOT = '/usr/share/'

CELERYD_LOG_LEVEL = 'INFO'
CELERY_REDIRECT_STDOUTS = True
CELERY_REDIRECT_STDOUTS_LEVEL = 'INFO'

RECAPTCHA_PUBLIC = '6LftU8USAAAAADia-hmK1RTJyqXjFf_T5QzqLE9o'

IGNORE_REDIS = True

ALARM_EMAIL = FEEDBACK_EMAILS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_HOST,
        'PORT': '3306'
        }
    }

DATABASES.update(uslogging_db)

USE_AMAZON_S3 = AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and DEFAULT_BUCKET

try:
    from settings_local import *
except ImportError:
    pass

if USE_AMAZON_S3:
    AWS_BUCKET_NAME = AWS_STORAGE_BUCKET_NAME


COMPRESS_MEDIA = not DEBUG
STATIC_URL_BASE = STATIC_URL
if COMPRESS_MEDIA:
    STATIC_URL += "%s/%s/" % (COMPRESS_OUTPUT_DIRNAME, LAST_COMMIT_GUID.split("/")[1])

ADMIN_MEDIA_PREFIX = "%sadmin/" % STATIC_URL_BASE

#  the keyd cache apps need this:
CACHE_TIMEOUT  = 60
CACHE_PREFIX  = "unisubscache"
