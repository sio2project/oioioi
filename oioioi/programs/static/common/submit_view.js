function getAllPiIds() {
    const piFields = $('#id_problem_instance_id option');
    let piIds = piFields.map(function() { return $(this).val(); }).get();
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
    const progLangs = new Map(Array.from(piIds, x => [x, '#id_prog_lang_' + x]));
    const languageFields = $(Array.from(progLangs.values()).join());

    function userInput() {
        const fileFieldVal = fileField.val();

        if (fileFieldVal)
            codeField.prop('disabled', true);
        else
            codeField.prop('disabled', false);

        if (fileFieldVal || !codeField.val())
            languageFields.prop('disabled', true);
        else
            languageFields.prop('disabled', false);

        if (fileFieldVal) {
            const hints_url = fileField.data("languagehintsurl");
            const dict = {pi_ids: piIds, filename: fileFieldVal, problemsite_key: window.problemsiteKey};
            $.getJSON(hints_url, dict, function(data) {
                progLangs.forEach(function(progLang, piId) {
                    $(progLang).val(data[piId]);
                });
            });
        }
    }

    if(fileField.length && codeField.length && languageFields.length) {
        codeField.on('input', userInput);
        fileField.on('input', userInput);
        userInput();
    }
});