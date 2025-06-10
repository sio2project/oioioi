import Clipboard from "clipboard";

$(window).on("load", function() {
    new Clipboard('.btn-copy')
        .on('success', function (e) {
            e.trigger.outerHTML = '<small><span class="fa-solid fa-check"></span>' + gettext("copied!") + '</small>';
        }).on('error', function (e) {
            e.trigger.outerHTML = '<small>' + gettext("Press Ctrl+C to copy") + '</small>';
        });
});