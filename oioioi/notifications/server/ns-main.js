#!/usr/bin/env node

/* Main notifications server program to be invoked from command line.
   Use: node ns-main.js for full usage information.
*/

function verify_dependencies() {
    try {
        require.resolve('commander');
        require.resolve('prettyjson');
        require.resolve('rabbit.js');
        require.resolve('socket.io');
        return true;
    } catch (ex) {
        console.error("Dependencies not met! Running auto-install...");
        child = require('child_process').exec('npm install', function (er) {
            console.error(er ? er : "");
            ns_main();
        });
        child.stdout.pipe(process.stdout);
        child.stderr.pipe(process.stderr);
        return false;
    }
}

function ns_main() {
    var program = require('commander');
    var pj = require('prettyjson');

    program
        .version('0.1.0')
        .option('-p, --port <n>', 'Server port (defaults to 7887)', parseInt)
        .option('-u, --url <s>', 'OIOIOI instance url (defaults to http://localhost:8000/)')
        .option('-a, --amqp <s>', 'RabbitMQ server url (defaults to amqp://oioioi:oioioi@broker)')
        .parse(process.argv);

    var config = {};
    config.amqp = program.amqp ? program.amqp : 'amqp://oioioi:oioioi@broker';
    config.port = program.port ? program.port : 7887;
    config['oioioi-url'] = program.url ? program.url : 'http://localhost:8000/';

    console.log('OIOIOI Notifications Server');
    console.log('Configuration:');
    console.log(pj.render(config));

    require('./notifications-server').runServer(config);
}

if (verify_dependencies()) {
    ns_main();
}
