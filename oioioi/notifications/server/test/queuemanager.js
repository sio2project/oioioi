var queuemanager = require('../queuemanager');
var rabbit = require('rabbit.js');
var assert = require('assert');

describe('QueueManager', function() {
    var context;
    before(function(done) {
        context = rabbit.createContext('amqp://localhost');
        queuemanager.init(context, done);
    });

    it ('should receive a message for user it is subscribed to', function(done) {
        var testDone = false;
        queuemanager.on('message', function(userName, message) {
            if (!testDone) {
                assert.equal(userName, 1);
                assert.equal(message.message, 'hello');
                assert.ok(queuemanager.acknowledge(1, "a"));
                done();
                testDone = true;
            }
        });
        queuemanager.subscribe(1);
        var push = context.socket('PUSH');
        push.connect(queuemanager.getQueueNameForUser(1), function() {
            push.write('{"id":"a", "message":"hello"}', 'utf8');
        });
    });

    it ('should not acknowledge an unknown message', function() {
       assert.ok(!queuemanager.acknowledge(2, 1));
    });


});