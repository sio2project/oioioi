var request = require("request");
var queuemanager = require('./queuemanager');

// maps sockets to user names
var sockets = {};
// maps users to socket collections
var users = {};

var session_id_cache = {};
var CONFIG;
var URL_AUTHENTICATE_SUFFIX = 'notifications/authenticate/';
var AUTH_CACHE_EXPIRATION_SECONDS = 300;

function init(config) {
    CONFIG = config;
    if (config) {
        config['oioioi-url'] += URL_AUTHENTICATE_SUFFIX;
    }
}

// Associates socket with user account.
// Parameters:
// socket - a valid socket.js socket instance
// sessionId - value of Django sessionid cookie (string)
// onCompleted - callback called with associated user name
// or null if login failed
function login(socket, sessionId, onCompleted) {
    auth(sessionId, function(userName) {
        if (!userName) {
            onCompleted(null);
            return;
        }
        sockets[socket.dict_id] = userName;
        if (!users[userName]) {
            users[userName] = {};
            queuemanager.subscribe(userName);
        }
        users[userName][socket.dict_id] = socket;
        onCompleted(userName);
    });

}

// Operation actually performing communication with OIOIOI instance
// in order to determine user's identity.
// Parameters: see login function
function auth(sessionId, onCompleted) {
    if (session_id_cache[sessionId]) {
        if (Date.now() < session_id_cache[sessionId].expires) {
            console.log('User ' + session_id_cache[sessionId].user + ' logged in from cache');
            onCompleted(session_id_cache[sessionId].user);
            return;
        }
    }

    request.post(
        CONFIG ? CONFIG['oioioi-url'] : 'bogus-url',
        { form: { nsid: sessionId } },
        function (error, response, body) {
            if (!error && response.statusCode === 200) {
                body = JSON.parse(body);
                if (body.status !== 'OK') {
                    console.log('Unable to authorize user!');
                    onCompleted(null);
                } else {
                    console.log('Authorized user: ' + body.user);
                    session_id_cache[sessionId] = {
                        user: body.user,
                        expires: Date.now() +
                            AUTH_CACHE_EXPIRATION_SECONDS * 1000
                    };
                    onCompleted(body.user);
                }
            } else {
                if (error) {
                    console.log('Unable to authorize user!');
                    console.log(error);
                    console.log('Make sure that OIOIOI instance is properly configured ' +
                        ' - tried to open URL: ' + CONFIG['oioioi-url']);
                }
                onCompleted(null);
            }
        }
    );
}

// Maps socket to associated user name.
function resolveUserName(socket) {
    return sockets[socket.dict_id];
}

// Returns socket.io sockets for given user name
// (used by message broadcasters).
function getClientsForUser(userName) {
    return users[userName];
}

// Removes a socket and, if it's the last socket associated with given user name,
// it unsubscribes from a queue for that user.
function logout(socket) {
    var userName = sockets[socket.dict_id];
    if (users[userName]) {
        delete users[userName][socket.dict_id];
        if (Object.keys(users[userName]).length === 0) {
            delete users[userName];
            console.log("No more users subscribed to queue " + userName + "! " +
                "Unsubscribing from queue.");
            queuemanager.unsubscribe(userName);
        }
    }
    delete sockets[socket.dict_id];
}

exports.init = init;
exports.login = login;
exports.logout = logout;
exports.resolveUserName = resolveUserName;
exports.getClientsForUser = getClientsForUser;
