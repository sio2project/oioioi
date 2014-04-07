#!/usr/bin/env node

/* Main notifications server program to be invoked from command line.
   Use: node ns-main.js for full usage information.
*/
var program = require('commander');
var pj = require('prettyjson');

function ns_main() {
    program
      .version('0.0.1')
      .option('-p, --port <n>', 'Server port (defaults to 7887)', parseInt)
      .option('-u, --url <s>', 'OIOIOI instance url (defaults to http://localhost:8000/)')
      .option('-a, --amqp <s>', 'RabbitMQ server url (defaults to amqp://localhost/)')
      .parse(process.argv);

    var config = {};
    config.amqp = program.amqp ? program.amqp : 'amqp://localhost';
    config.port = program.port ? program.port : 7887;
    config['oioioi-url'] = program.url ? program.url : 'http://localhost:8000/';

    console.log('OIOIOI Notifications Server');
    console.log('Configuration:');
    console.log(pj.render(config));

    require('./notifications-server').runServer(config);
}

ns_main();