#!/bin/bash
source /usr/local/bin/config_env

cd $APP_DIR/deploy
$VE_DIR/bin/pip install -r requirements-test.txt

cd $APP_DIR
cp dev_settings_test.py test_settings.py
cat << EOF >> test_settings.py
BROKER_HOST = "$TEST_IPADDR"
BROKER_PORT = $TEST_BROKER_PORT
BROKER_USER = 'guest'
BROKER_PASSWORD = 'guest'

HAYSTACK_SOLR_URL = "http://$TEST_IPADDR:$TEST_SOLR_PORT/solr/"
export DJANGO_LIVE_TEST_SERVER_ADDRESS='localhost:8000, 8001, 8080, 8888, 9000, 9001, 9090, 9999, 7000, 7070, 7777'

INSTALLED_APPS = INSTALLED_APPS + ('django_nose','webdriver_testing')
EOF

CMD="$VE_DIR/bin/python manage.py test webdriver_testing --settings=test_settings --with-xunit"

echo "Running Tests..."
$CMD
