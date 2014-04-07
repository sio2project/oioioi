var rabbit = require('rabbit.js');
var EventEmitter = require('events').EventEmitter;
var eventEmitter = new EventEmitter();
var context;
var workers = {};
var unackMessages = {};
var QUEUE_PREFIX = '_notifs_';
/* Initializes the QueueManager.
   Parameters: _context - RabbitMQ context,
               onCompleted - callback called with no arguments
*/
function init(_context, onCompleted) {
    if (!_context) {
        throw new TypeError();
    }
    context = _context;

    context.on('ready', function() {
        onCompleted();
    });
    context.on('error', function(e) {
        console.log('RabbitMQ error!');
        console.log(e.toString());
    });
}

function getQueueNameForUser(userId) {
    return QUEUE_PREFIX + userId;
}

// Subscribes to queue associated with given userId.
// From now on, server will be notified of messages addressed to given user.
function subscribe(userId) {
    if (workers[userId]) {
        return;
    }
    workers[userId] = context.socket('WORKER');
    workers[userId].connect(getQueueNameForUser(userId));
    unackMessages[userId] = {};

    workers[userId].on('data', function(data) {
       try {
           data = JSON.parse(data);
       } catch(obj) {
           // remove bad message from queue
           console.log('Bad message format arrived!');
           workers[userId].ack();
       }
       unackMessages[userId][data.id] = data;
       eventEmitter.emit('message', userId, data);
    });
}

// Unsubscribes from queue associated with given userId.
function unsubscribe(userId) {
    if (!workers[userId]) {
        return;
    }
    workers[userId].close();
    delete workers[userId];
}

// Unsubscribes from all queues. I'm not sure if this is used anywhere.
function unsubscribeAll() {
    for (var userId in workers) {
        unsubscribe(userId);
    }
}

/* Acknowledges a message, removing it from RabbitMQ queue and internal cache.
   It is considered as read and no longer exists in the system.
   No socket will receive it anymore. */
function acknowledge(userId, messageId) {
    if (unackMessages[userId] &&
        Object.keys(unackMessages[userId])[0] === messageId) {
        workers[userId].ack();
        delete unackMessages[userId][messageId];
        console.log('Acknowledged msgid '+ messageId);
        return true;
    }
    return false;
}

// Returns all messages that have not been acknowledged yet.
function getUnacknowledgedMessages(userId) {
    return unackMessages[userId];
}

exports.init = init;
exports.getUnacknowledgedMessages = getUnacknowledgedMessages;
exports.subscribe = subscribe;
exports.unsubscribe = unsubscribe;
exports.acknowledge = acknowledge;
exports.unsubscribeAll = unsubscribeAll;
exports.getQueueNameForUser = getQueueNameForUser;
exports.on = eventEmitter.on.bind(eventEmitter);
