$(function(){
    var sync_time = 300000 + (Math.random()*60000)|0;
    var sync_interval;
    var status_url = oioioi_base_url + "status";

    var fetchUpdates = function() {
        $.getJSON(status_url, function(data) {
           $(window).trigger('updateStatus', data);
        });
   };

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
