var rabbit = require('rabbit.js');
var debug = require('debug')('queuemanager');
var EventEmitter = require('events').EventEmitter;
var eventEmitter = new EventEmitter();
var context;
var workers = {};
var unackMessages = {};
var rabbit_ready = false;
var QUEUE_PREFIX = '_notifs_';
var RETRY_WAIT = 1000 * 30;
/* Initializes the QueueManager.
   Parameters: url - RabbitMQ url,
               onCompleted - callback called with no arguments
*/
function init(url, onCompleted) {
    if (!url) {
        throw new TypeError("No rabbitmq url passed to queuemanager");
    }

    var workers_connected = Object.keys(workers);

    function reconnectWorkers() {
        debug('Reconnecting workers!');
        workers_connected.forEach(function(id) {
            subscribe(id);
        });
    }

    function initContext(callback) {
        debug('Initializing rabbitmq context');
        workers = {};
        unackMessages = {};

        context = rabbit.createContext(url);

        context.on('ready', function() {
            console.log('Rabbit connected!');
            rabbit_ready = true;
            reconnectWorkers(workers_connected);
            if (callback) {
                callback();
                callback = null;
            }
        });
        context.on('error', function(e) {
            console.log('RabbitMQ error!');
            console.log(e.toString());
            if (e.message.indexOf('CONNECTION-FORCED') > -1) {
                rabbit_ready = false;
                workers_connected = Object.keys(workers);
            } else if (e.message.indexOf('ECONNREFUSED') > -1) {
                console.log('Connection refused... Trying again');
                setTimeout(function() { initContext(callback); }, RETRY_WAIT);
            }
        });
        context.on('close', function() {
            console.log('Rabbit closed connection! Handling error...');
            rabbit_ready = false;
            setTimeout(function() { initContext(callback); }, RETRY_WAIT);
        });
    }

    initContext(onCompleted);
}

function getQueueNameForUser(userId) {
    return QUEUE_PREFIX + userId;
}

// Subscribes to queue associated with given userId.
// From now on, server will be notified of messages addressed to given user.
function subscribe(userId) {
    debug('subscribing for ' + userId);
    if (workers[userId] || !rabbit_ready) {
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
        debug(userId + ': received ' + data);
    });
}

// Unsubscribes from queue associated with given userId.
function unsubscribe(userId) {
    if (!workers[userId]) {
        return;
    }
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
        debug('Acknowledged msgid '+ messageId);
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
