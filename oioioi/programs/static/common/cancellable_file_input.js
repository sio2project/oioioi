/**
 *  Cancels file input after clicking the 'x' button.
 */
$(function() {
    const cancel = $('.file_cancel_button');
    cancel.click(function() {
        const file = $('input', $(this).parent());
        file.val('');
        file.trigger('input');
    });
});