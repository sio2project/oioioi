function add_question_content() {
    var elem = $('textarea#id_content');
    var content = $('.message_to_quote:first').text() + '\n\n' + elem.val();

    /* This moves the cursor to the end. */
    elem.focus().val('').val(content);
    elem.scrollTop(elem[0].scrollHeight);

    $('#respond_inline').hide();
}
