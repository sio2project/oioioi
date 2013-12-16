function add_question_content() {
    var elem = $('textarea#id_content');
    var content = $('.message_to_quote:first').text() + '\n\n' + elem.val();

    /* This moves the cursor to the end. */
    elem.focus().val('').val(content);
    elem.scrollTop(elem[0].scrollHeight);

    $('#respond_inline').hide();
}

function get_reply_templates(url, inc_url) {
    $.getJSON(url, function(data) {
        if(data.length == 0)
        {
            $('div.include-template').hide()
            return;
        }
        var items = [];
        $.each(data, function(_index, val) {
            items.push('<li><a data-id="' + val["id"] + '" ' +
                              'href="#" ' +
                              'class="include-reply-template" ' +
                              'id="reply_template_' + val["id"] + '" ' +
                              'title="' + val["content"] + '">' +
                              val["name"] +
                              '</a></li>');
        });
        $('.template-replies').html(items);
        $('a.include-reply-template').click(function() {
            include_reply_template($(this).data('id'), inc_url);
            return false;
        });
    });
}

function include_reply_template(id, inc_url) {
    var elem = $('textarea#id_content');
    var text = elem.val() + $('#reply_template_' + id).attr('title');

    $.get(inc_url + id + '/');

    elem.focus().val('').val(text);
    elem.scrollTop(elem[0].scrollHeight);
}
