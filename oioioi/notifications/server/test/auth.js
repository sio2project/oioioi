var assert = require('assert');
var auth = require('../auth');
var sinon = require('sinon');
var request = require('request');
var queuemanager = require('../queuemanager');
var rabbit = require('rabbit.js');

describe('Authentication Module', function() {
    before(function (done) {
        var poster = sinon.stub(request, 'post');
        poster.withArgs(sinon.match.any,
            sinon.match({form:{nsid: '12345'}}))
            .yields(null, {statusCode: 200}, '{"status": "UNAUTHORIZED"}');
        poster.withArgs(sinon.match.any,
            sinon.match({form:{nsid: 'TEST_USER_SID'}}))
            .yields(null, {statusCode: 200}, '{"status": "OK", "user": "test_user"}');
        queuemanager.init('amqp://oioioi:oioioi@broker', done);
    });


    after(function () {
        request.post.restore();
    });

    afterEach(queuemanager.unsubscribeAll);

    it('should not auth an invalid user', function(done) {
        auth.login({dict_id: 1}, '12345', function(userName) {
            assert.equal(userName, null);
            done();
        });
    });

    it('should auth a valid user', function(done) {
        var socket = {dict_id: 1};
        auth.login(socket, 'TEST_USER_SID', function(userName) {
            assert.equal(userName, "test_user");
            auth.logout(socket);
            done();
        });
    });

    it ('when 2 sockets log in, then log out, user should be sub/unsubscribed once', function(done) {
        subSpy = sinon.spy(queuemanager, "subscribe");
        unsubSpy = sinon.spy(queuemanager, "unsubscribe");
        auth.login({dict_id: 1}, 'TEST_USER_SID', function() {
            auth.login({dict_id: 2}, 'TEST_USER_SID', function() {
                assert.ok(subSpy.calledOnce);
                auth.logout({dict_id: 1});
                assert.ok(!unsubSpy.called);
                auth.logout({dict_id: 2});
                assert.ok(unsubSpy.calledOnce);
                done();
            });
        });
    });
});

