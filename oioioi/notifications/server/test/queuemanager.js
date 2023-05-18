var queuemanager = require('../queuemanager');
var rabbit = require('rabbit.js');
var assert = require('assert');

describe('QueueManager', function() {
    before(function(done) {
        queuemanager.init('amqp://oioioi:oioioi@broker', done);
    });

    it ('should receive a message for user it is subscribed to', function(done) {
        var testDone = false;
        queuemanager.on('message', function(userName, message) {
            if (!testDone) {
                assert.equal(userName, 1);
                assert.equal(message.message, 'hello');
                done();
                testDone = true;
            }
        });
        queuemanager.subscribe(1);
        var push = rabbit.createContext('amqp://oioioi:oioioi@broker').socket('PUSH');
        push.connect(queuemanager.getQueueNameForUser(1), function() {
            push.write('{"id":"a", "message":"hello"}', 'utf8');
        });
    });

});
