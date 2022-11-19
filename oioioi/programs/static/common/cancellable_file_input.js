/**
 *  Cancels file input after clicking the 'x' button.
 */
$(function() {
    const cancelFields = $('.file_cancel_button');
    const fileInputs = $('input', cancelFields.parent());

    cancelFields.click(function() {
        const file = $('input', $(this).parent());

        file.val('');
        file.trigger('input');
    });

    function cancelButtonShowHide() {
        const file = $(this);
        const cancel = $('.file_cancel_button', file.parent());

        if (file.val())
            cancel.show();
        else
            cancel.hide();
    }

    if (fileInputs.length) {
        fileInputs.on('input', cancelButtonShowHide);
        fileInputs.each(cancelButtonShowHide);
    }
});