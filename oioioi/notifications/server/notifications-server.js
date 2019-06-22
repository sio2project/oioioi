var http = require('http'),
    debug = require('debug')('server'),
    io = require('socket.io'),
    rabbit = require('rabbit.js'),
    auth = require('./auth'),
    queuemanager = require('./queuemanager');

var last_dict_id = 0;
var app;
var CONFIG;

/* Everywhere in this code, "socket" as function argument is considered as
   socket.io socket instance created as a result of accepting connection. */

// Specifies default behavior for internal HTTP server.
function httpRequestHandler(_, res) {
    res.writeHead(200);
    res.end("Welcome to OIOIOI Notifications Server.\n" +
        "This server is available for purpose of serving online notifications.\n" +
        "This server does not host a functional website itself.");
}

// Called whenever new socket has connected to server.
function onSocketConnected(socket) {
    configureSocket(socket);
}

// Prepares socket to be used in the system.
function configureSocket(socket) {
    socket.dict_id = last_dict_id++;
    debug("Connected socket " + socket.dict_id);
    socket.on('authenticate', respond('authenticate', socket, onAuthenticateRequested));
    socket.on('disconnect', onDisconnect(socket));
}

// Called whenever new socket has disconnected from server.
function onDisconnect(socket) {
    return function() {
        debug("Disconnected socket " + socket.dict_id);
        auth.logout(socket);
    };
}

// Initializes HTTP socket server and RabbitMQ context.
function runServer(config) {
    CONFIG = config;
    auth.init(config);
    queuemanager.init(CONFIG.amqp, function() {
        app = http.createServer(httpRequestHandler);
        queuemanager.on('message', onRabbitMessage);
        io.listen(app).sockets.on('connection', onSocketConnected);
        app.listen(CONFIG.port);
        console.log('Notifications Server listening on port ' + CONFIG.port);
    });
}

/* Middleware used for handling user requests.
   Parameters: key - command string,
               socket - current socket.io socket instance,
               handler - response handling function called with parameters:
                    data - JSON-parsed data,
                    username - null or authenticated user name,
                    socket - current socket.io socket instance,
                    response callback - to be called with single string
                        when response is ready.
 */
function respond(key, socket, handler) {
    return function(data) {
        var userName = auth.resolveUserName(socket);
        handler(JSON.parse(data), userName, socket, function(response) {
            socket.emit(key, response);
        });
    };
}

// Called whenever a message is received - message is an object.
function onRabbitMessage(userName, message) {
    debug('Got message from ' + userName + ' queue: ' +
          JSON.stringify(message));
    var clients = auth.getClientsForUser(userName);
    for (var clientId in clients) {
        clients[clientId].emit("message", message);
    }
}

/* Called whenever an authentication is requested by socket.
   Upon successful completion, all messages addressed to associated user
   will be forwarded to this socket until it disconnects.
   Parameters: see respond -> handler.
 */
function onAuthenticateRequested(data, _, socket, onCompleted) {
    if (!data || !data.session_id) {
        return {status: 'ERR_INVALID_MESSAGE'};
    }
    auth.login(socket, data.session_id, function(userName) {
        onCompleted(userName ? {status: 'OK'} : {status: 'ERR_AUTH_FAILED'});
        // when a new user logs in, let him know what's up!
    });
}

exports.onSocketConnected = onSocketConnected;
exports.onRabbitMessage = onRabbitMessage;
exports.runServer = runServer;
