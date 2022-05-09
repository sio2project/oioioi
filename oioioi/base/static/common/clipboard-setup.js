$(window).on("load", function() {
    new Clipboard('.btn-copy')
        .on('success', function (e) {
            e.trigger.outerHTML = '<small><span class="glyphicon glyphicon-ok"></span>' + gettext("copied!") + '</small>';
        }).on('error', function (e) {
            e.trigger.outerHTML = '<small>' + gettext("Press Ctrl+C to copy") + '</small>';
        });
});