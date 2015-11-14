$(function(){
    var STALE_PROMISE_TIME = 3000;

    var promise_pending = null;
    var sync_time = 300000 + (Math.random()*60000)|0;
    var sync_interval;
    var status_url = oioioi_base_url + "status";

    var update_status_promise = function() {
        var data = null;

        var dfd = $.Deferred()
        .done(function() {
            promise_pending = null;
            $(window).trigger('updateStatus', data);
        })
        .fail(function() {
            // If we fail, we try to fullfill a promise again
            promise_pending = null;
            $(window).trigger('updateStatusRequest');
        });

        var json_request = $.getJSON(status_url, function(aData) {
            data = aData;
        });

        $.when(json_request)
        .done(function() {
            dfd.resolve();
        })
        .fail(function() {
            dfd.reject();
        });

        setTimeout(function() {
            json_request.abort();
        }, STALE_PROMISE_TIME);

        return dfd.promise();
    };

    var fetchUpdates = function() {
        $(window).trigger('updateStatusRequest');
    };

    $(window).on('updateStatusRequest', function() {
        if (promise_pending === null) {
            promise_pending = update_status_promise();
        }
    });

    $(window).one('initialStatus', function(ev, data) {
        if (data.sync_time) {
            sync_time = data.sync_time + (Math.random()*data.sync_time*0.05)|0;
        }
        if (data.status_url) {
            status_url = data.status_url;
        }
        sync_interval = setInterval(fetchUpdates, sync_time);
    });

    $('#modal-outdated').on('hidden', function() {$(this).detach();});
});
