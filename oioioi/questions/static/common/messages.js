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

$.fn.toggleChevron = function() {
    return $(this).attr('class') == 'icon-chevron-up' ?
            $(this).chevronExpand() : $(this).chevronCollapse();
}

$.fn.chevronCollapse = function() {
    return $(this).attr('class', 'icon-chevron-up');
}

$.fn.chevronExpand = function() {
    return $(this).attr('class', 'icon-chevron-down');
}

$.fn.setMsgHeight = function() {
    $(this).children('td').css('height', $(this).find('div').css('height'));
}

$(document).ready(function() {
    var msgs = $("[id*='hidden_message_']");
    var msg_bars = $("[id*='message_']");
    var msg_buttons = $("[id*='show_message_']");
    var expand_text = gettext("Expand all messages");
    var collapse_text = gettext("Collapse all messages");
    var single_expand_text = gettext("Expand message");
    var single_collapse_text = gettext("Collapse message");
    var expand = true;
    var btn = $('a#expand_messages');
    var speed = 200;
    var message_on_expand = function(msg) {
        if ($(msg).attr("data-is-new") == 1)
        {
            $.ajax({
                 type: 'GET',
                 url: $(msg).attr("data-visit-url"),
            });

            $(msg).removeAttr("data-visit-url");
            $(msg).attr("data-is-new", 0);
            $(msg).prev().find(".new-msg-label").remove();
        }
    };

    btn.text(expand_text);
    msg_buttons.attr('title', single_expand_text);
    msgs.find('div').css('position', 'absolute');

    btn.click(function() {
        if (expand)
            msgs.each(function() {
                $(this).show(speed);
                $(this).setMsgHeight();
                message_on_expand(this);
            });
        else
            msgs.hide(speed);


        $(this).text(expand ? collapse_text : expand_text);
        msg_buttons.children('i').each(function() {
            if (expand)
                $(this).chevronCollapse();
            else
                $(this).chevronExpand();
        });
        expand = !expand;
    });

    msg_bars.mouseenter(function() {
        $(this).children('td#msg_buttons').fadeTo(1, 1);
    });

    msg_bars.mouseleave(function() {
        $(this).children('td#msg_buttons').fadeTo(1, 0);
    });

    msg_buttons.click(function() {
        var s = $(this).attr('id');
        var hidden_msg =
                $('#hidden_message_' + parseInt(s.substring(13, s.length)));

        hidden_msg.toggle(speed);
        hidden_msg.setMsgHeight();
        message_on_expand(hidden_msg);

        $(this).children('i').toggleChevron();
        $(this).attr('title', $(this).attr('title') == single_expand_text ?
                single_collapse_text : single_expand_text);
    });
});