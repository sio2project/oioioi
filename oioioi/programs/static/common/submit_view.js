function getAllPiIds() {
    const piField = $('#id_problem_instance_id option');
    let piIds = piField.map(function() { return $(this).val() }).get();
    piIds = piIds.filter(i => i !== "");
    return piIds;
}

/**
 * Works in submit view in order to update program languages picker and code
 * field based on the user input to code and file fields.
 */
$(function() {
    const piIds = getAllPiIds();
    const fileField = $('#id_file');
    const codeField = $('#id_code');
    const progLangs = piIds.map(x => '#id_prog_lang_' + x).join()
    const languageFields = $(progLangs);

    function userInput() {
        if (fileField.val())
            codeField.prop('disabled', true);
        else
            codeField.prop('disabled', false)

        if (fileField.val() || !codeField.val())
            languageFields.prop('disabled', true);
        else
            languageFields.prop('disabled', false);
    }

    if(fileField.length && codeField.length && languageFields.length) {
        codeField.on('input', userInput);
        fileField.on('input', userInput);
        userInput();
    }
});