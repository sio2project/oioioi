An optional module for transmitting instant notifications to users.
It consists of a Django app and a Node.js server passing notifications.

How to use:
- install Node.js
- install and run rabbitmq-server

How to run the Notifications Server:
Invoke: ./manage.py notifications_server
(when launched first time, dependencies will be installed and application will
exit - just relaunch it after it's done)

If required, modify appropriate settings in settings.py file - their names begin
with "NOTIFICATIONS_" prefix.

How to run tests:
- in ./server directory, invoke: npm test

How to notify users manually:
- invoke: ./manage.py notify [options]

To see options, use: ./manage.py notify --help

For development purposes, you can use the following settings with docker-compose-dev setup:

NOTIFICATIONS_SERVER_ENABLED = True
NOTIFICATIONS_RABBITMQ_URL = 'amqp://oioioi:oioioi@broker'
NOTIFICATIONS_SERVER_URL = 'http://localhost:7887/'

Additionally, you need to expose port 7887 for web container in docker-compose-dev.yml
It is recommended to install npm and nodejs inside web container.
RabbitMq is already installed in broker container.
