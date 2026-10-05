if (!String.prototype.fmt) {
    String.prototype.fmt = function(dict) {
        return interpolate(this, dict, true);
    };
}

if (!String.prototype.startsWith) {
    Object.defineProperty(String.prototype, 'startsWith', {
        enumerable: false,
        configurable: false,
        writable: false,
        value: function (searchString, position) {
            position = position || 0;
            return this.indexOf(searchString, position) === position;
        }
    });
}

function scroll_to(selector) {
    $('html, body').scrollTop($(selector).offset().top);
}

function scroll_and_focus(selector) {
    scroll_to(selector);
    $(selector).focus();
}

window.scroll_to = scroll_to
window.scroll_and_focus = scroll_and_focus
