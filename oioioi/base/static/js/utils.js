if (!String.prototype.fmt) {
    String.prototype.fmt = function(dict) {
        return interpolate(this, dict, true);
    };
}

function scroll_to(selector) {
    $('html, body').scrollTop($(selector).offset().top);
}

function scroll_and_focus(selector) {
    scroll_to(selector);
    $(selector).focus();
}

// Disables the button and shows its data-loading-text, or restores it (replaces Bootstrap 3's .button('loading')).
function set_button_loading(button, loading) {
    const $button = $(button);
    if (loading) {
        $button.data('original-html', $button.html());
        $button.text($button.data('loading-text'));
    } else if ($button.data('original-html') !== undefined) {
        $button.html($button.data('original-html'));
    }
    $button.prop('disabled', loading);
}

window.scroll_to = scroll_to
window.scroll_and_focus = scroll_and_focus
window.set_button_loading = set_button_loading
