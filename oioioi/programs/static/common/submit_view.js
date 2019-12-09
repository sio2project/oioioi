/**
 * Works in submit view in order to update program languages picker and code
 * field based on the user input to code and file fields.
 */
$(function() {
    const fileField = $('#id_file');
    const codeField = $('#id_code');
    const languageField = $('#id_prog_lang');

    function userInput() {
        if (fileField.val())
            codeField.prop('disabled', true);
        else
            codeField.prop('disabled', false)

        if (fileField.val() || !codeField.val())
            languageField.prop('disabled', true);
        else
            languageField.prop('disabled', false);
    }

    if(fileField.length && codeField.length && languageField.length) {
        codeField.on('input', userInput);
        fileField.on('input', userInput);
        userInput();
    }
});
