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

DEV, STAGING, PRODUCTION = range(1, 4)

INSTALLATION = INSERT_INSTALLATION_HERE # one of DEV, STAGING, PRODUCTION

from settings import AUTHENTICATION_BACKENDS

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_USER_DATA_BUCKET_NAME = 'INSERT USERDATA BUCKET'

# Celery broker settings
BROKER_BACKEND = 'amqplib'
BROKER_HOST     = "INSERT BROKER HOST"
BROKER_PASSWORD = "INSERT BROKER PASSWORD"
BROKER_PORT     = INSERT BROKER PORT
BROKER_USER     = "INSERT BROKER USER"
BROKER_VHOST    = "INSERT BROKER VHOST"

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

DATABASE_HOST = 'INSERT DB HOST'
DATABASE_NAME = 'INSERT DATABASE NAME'
DATABASE_PASSWORD = 'INSERT DATABASE PASSWORD'
DATABASE_USER = 'INSERT DATABASE USER'

DEFAULT_BUCKET = '' # special note: should be blank for dev.

# Handy to temporarily route Django email messages to a file
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/unisubs-messages'

EMAIL_NOTIFICATION_RECEIVERS = (INSERT EMAIL NOTIFICATION RECEIVERS)

ENABLE_METRICS = True

FACEBOOK_API_KEY = FACEBOOK_APP_ID = 'INSERT FACEBOOK APP ID'
FACEBOOK_SECRET_KEY = 'INSERT FACEBOOK SECRET KEY'

HAYSTACK_SOLR_URL = 'http://localhost:38983/solr'

MEDIA_URL = 'INSERT MEDIA_URL'

PROMOTE_TO_ADMINS = []

RECAPTCHA_SECRET = ''

REDIS_HOST = CELERY_REDIS_HOST = 'INSERT REDIS HOST'
REDIS_PORT = CELERY_REDIS_PORT = INSERT REDIS PORT

RIEMANN_HOST = 'INSERT RIEMANN HOST'

SECRET_KEY = 'INSERT SITE SECRET KEY'
SEND_ERROR_REPORT_TO = (INSERT ERROR REPORT TO)
SENTRY_DSN = 'INSERT SENTRY DSN'
STATIC_URL = 'INSERT STATIC_URL'

TWITTER_CONSUMER_KEY = 'INSERT TWITTER CONSUMER KEY'
TWITTER_CONSUMER_SECRET = 'INSERT TWITTER CONSUMER SECRET'

if INSTALLATION == STAGING or INSTALLATION == PRODUCTION:
    uslogging_db = {
        'uslogging': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'INSERT USLOGGING DB NAME',
            'USER': 'INSERT USLOGGING DB USER',
            'PASSWORD': 'INSERT USLOGGING DB PASSWORD',
            'HOST': 'INSERT USLOGGING DB HOST',
            'PORT': '3306'
            }
        }
    USLOGGING_DATABASE = 'INSERT USLOGGING DATABASE'
else:
    uslogging_db = {}

VIMEO_API_KEY = 'INSERT VIMEO API KEY'
VIMEO_API_SECRET = 'INSERT VIMEO API SECRET'

YOUTUBE_API_SECRET = 'INSERT YOUTUBE API SECRET'
YOUTUBE_CLIENT_ID = 'INSERT YOUTUBE CLIENT ID'
YOUTUBE_CLIENT_SECRET = 'INSERT YOUTUBE CLIENT SECRET'

