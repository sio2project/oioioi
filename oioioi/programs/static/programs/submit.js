/**
 * Updates program languages picker based on code field.
 */
$(function() {
    const codeField = $('#id_code');
    const languagePicker = $('#id_prog_lang');

    function updateLanguagePicker() {
        if (codeField.val().length === 0) {
            languagePicker.prop('disabled', true);
        } else {
            languagePicker.prop('disabled', false);
        }
    }

    codeField.bind('input propertychange', updateLanguagePicker);
    updateLanguagePicker();
});
