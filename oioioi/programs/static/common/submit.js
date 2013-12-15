function handle_prog_lang_updates() {
    var code_field = $('#id_code')
    var prog_lang_field = $('#id_prog_lang')
    function update_prog_lang_field() {
        if (code_field.val().length == 0)
            prog_lang_field.prop('disabled', true);
        else
            prog_lang_field.prop('disabled', false);
    }
    $('#id_code').bind('input propertychange', update_prog_lang_field);
    update_prog_lang_field();
}
