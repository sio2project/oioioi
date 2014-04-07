How to prepare:
- install Node.js
- install and run rabbitmq-server
- in this directory, invoke: npm install (with Internet connection)

How to run this server:
Invoke: node ns-main [options]
Options:

-h, --help      output usage information
-V, --version   output the version number
-p, --port <n>  Server port (defaults to 7887)
-u, --url <s>   OIOIOI instance url (defaults to http://localhost:8000/)
-a, --amqp <s>  RabbitMQ server url (defaults to amqp://localhost/)

How to run tests:
- in this directory, invoke: npm test

How to test message delivery:
- type: node messager.js target-user-name message
and watch the message arrive to target user.

This module is an integral part of OIOIOI.