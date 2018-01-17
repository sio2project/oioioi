var newAnswersConfig = {};
newAnswersConfig.pollingTimeout = 5000;
newAnswersConfig.loadDateSeconds = 0;
newAnswersConfig.visited = {};
newAnswersConfig.toDismiss = 0;
newAnswersConfig.id = 0;

function add_question_content() {
    var elem = $('textarea#id_content'),
        content = $('.message_to_quote:first').text() + '\n\n' + elem.val();

    /* This moves the cursor to the end. */
    elem.focus().val('').val(content);
    elem.scrollTop(elem[0].scrollHeight);

    $('#respond_inline').hide();
}

function get_reply_templates(url, inc_url) {
    $.getJSON(url, function(data) {
        if(data.length == 0)
        {
            $('div.include-template').hide();
            return;
        }
        var items = [];
        $.each(data, function(_index, val) {
            items.push('<li><a data-id="' + val.id + '" ' +
                              'href="#" ' +
                              'class="include-reply-template" ' +
                              'id="reply_template_' + val.id + '" ' +
                              'title="' + val.content + '">' +
                              val.name +
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

// This function is invoked in template script in order to initialize
// new answers checking polls

function beginCheckAnswersInMeantime(url, initialDate) {
    newAnswersConfig.loadDateSeconds = initialDate;
    newAnswersConfig.url = url;
    checkAnswersInMeantime();
}

// This function checks if any new answers were made in the meantime
// after user started composing an answer.

function checkAnswersInMeantime() {
    var currentUrl = newAnswersConfig.url;
    $.getJSON(currentUrl,
        {'timestamp': Math.round(newAnswersConfig.loadDateSeconds)},
        function (data) {
        newAnswersConfig.loadDateSeconds = data.timestamp;
        $.each(data.messages, function (key, val) {
            var topic = val[0], msg = val[1], msg_id = val[2];
            if (newAnswersConfig.visited[msg_id]) {
                return;
            }

            newAnswersConfig.toDismiss++;
            $('#submitter').prop('disabled', true);
            $("#disabled-text").show();
            newAnswersConfig.visited[msg_id] = true;
            var alertFormatted = alertText
                    .replace('%content%', msg)
                    .replace('%id%', msg_id)
                    .replace('%id%', msg_id);
            $('#alerts').append(alertFormatted);
            $('#alert_' + msg_id).hide();
            $('#alert_' + msg_id).fadeIn();
        });
    })
    .complete(function () {
        setTimeout(checkAnswersInMeantime, newAnswersConfig.pollingTimeout);
    });
    newAnswersConfig.loadDateSeconds = Date.now() / 1000;
}

function new_answer_reload_page() {
    $("#just_reload").val("yes");
    $("#reply_form").submit();
}

function dismissNewMessageAlert(id) {
    newAnswersConfig.toDismiss--;
    if (newAnswersConfig.toDismiss == 0) {
        $('#submitter').prop('disabled', false);
        $("#disabled-text").hide();
    }
    $("#alert_" + id).fadeOut();
}

$.fn.setMsgHeight = function() {
    $(this).children('td').css('height', $(this).find('div').css('height'));
};
