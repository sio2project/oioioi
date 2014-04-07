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
