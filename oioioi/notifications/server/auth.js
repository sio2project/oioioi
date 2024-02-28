var debug = require('debug')('auth');
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
    auth(sessionId, function (userName) {
        if (!userName) {
            onCompleted(null);
            return;
        }
        sockets[socket.data.dict_id] = userName;
        if (!users[userName]) {
            users[userName] = {};
            queuemanager.subscribe(userName);
        }
        users[userName][socket.data.dict_id] = socket;
        onCompleted(userName);
    });

}

// Operation actually performing communication with OIOIOI instance
// in order to determine user's identity.
// Parameters: see login function
async function auth(sessionId, onCompleted) {
    if (session_id_cache[sessionId]) {
        if (Date.now() < session_id_cache[sessionId].expires) {
            debug('User ' + session_id_cache[sessionId].user +
                ' logged in from cache');
            onCompleted(session_id_cache[sessionId].user);
            return;
        }
    }
    /**
     * @type {Response | undefined}
     */
    let response;
    /**
     * @type {string | undefined}
     */
    let body;
    /**
     * @type {unknown}
     */
    let error;
    try {
        response = await fetch(
            CONFIG ? CONFIG['oioioi-url'] : 'bogus-url',
            {
                method: "POST",
                body: `nsid=${encodeURIComponent(sessionId)}`,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            },
        );
        body = await response.text();
    } catch (err) {
        error = err;
    }
    if (error || response == null || body == null) {
        console.log('Unable to authorize user!');
        console.log(error);
        console.log('Make sure that OIOIOI instance is properly configured ' +
            ' - tried to open URL: ' + CONFIG['oioioi-url']);
        onCompleted(null);
        return;
    }
    if (response.status === 200) {
        const json = JSON.parse(body);
        if (json.status !== 'OK') {
            console.log('Unable to authorize user!');
            onCompleted(null);
        } else {
            debug('Authorized user: ' + json.user);
            session_id_cache[sessionId] = {
                user: json.user,
                expires: Date.now() +
                    AUTH_CACHE_EXPIRATION_SECONDS * 1000
            };
            onCompleted(json.user);
        }
    }
}

// Maps socket to associated user name.
function resolveUserName(socket) {
    return sockets[socket.data.dict_id];
}

// Returns socket.io sockets for given user name
// (used by message broadcasters).
function getClientsForUser(userName) {
    return users[userName];
}

// Removes a socket and, if it's the last socket associated with given user name,
// it unsubscribes from a queue for that user.
function logout(socket) {
    var userName = sockets[socket.data.dict_id];
    if (users[userName]) {
        delete users[userName][socket.data.dict_id];
        if (Object.keys(users[userName]).length === 0) {
            delete users[userName];
            debug("No more users subscribed to queue " + userName + "! " +
                "Unsubscribing from queue.");
            queuemanager.unsubscribe(userName);
        }
    }
    delete sockets[socket.data.dict_id];
}

exports.init = init;
exports.login = login;
exports.logout = logout;
exports.resolveUserName = resolveUserName;
exports.getClientsForUser = getClientsForUser;
