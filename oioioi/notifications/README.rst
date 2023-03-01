An optional module for transmitting instant notifications to users.
It consists of a Django app and a Node.js server passing notifications.

How to use:
- expose port 7887 for web container in docker-compose-dev.yml
- open container bash (easy_toolbox.py bash)
- install Node.js (sudo apt install nodejs npm)
- uncomment notifications from INSTALLED_APPS in settings.py
- uncomment notifications from context_processors in settings.py
- set following settings in settings.py:
    NOTIFICATIONS_SERVER_ENABLED = True
    NOTIFICATIONS_RABBITMQ_URL = 'amqp://oioioi:oioioi@broker'
    NOTIFICATIONS_SERVER_URL = 'http://localhost:7887/'
- stop and start again the containers (easy_toolbox.py stop; easy_toolbox.py start)



How to run the Notifications Server manually(inside container):
- install and run rabbitmq_server
- Invoke: ./manage.py notifications_server

If required, modify appropriate settings in settings.py file - their names begin
with "NOTIFICATIONS_" prefix.


How to run tests:
- in ./server directory, invoke: npm test

How to notify users manually:
- invoke: ./manage.py notify [options]

To see options, use: ./manage.py notify --help
