$(function() {
    var rowTemplate =
        '<tr>' +
            '<td class="color-cell"></td>' +
            '<td class="team-cell">' +
                '__TEAM__' +
            '</td>' +
            '<td class="button-cell"></td>' +
        '</tr>';
    var deliveredButtonTemplate =
        '<button class="btn btn-primary btn-sm" ' +
            'data-loading-text="' + gettext("Delivering...") + '">' +
            gettext("Delivered") +
        '</button>';
    var notDeliveredButtonTemplate =
        '<button class="btn btn-danger btn-sm"' +
            ' data-loading-text="' + gettext("Taking back...") + '">' +
            gettext("Not delivered") + '</button>';
    var firstAcceptedTemplate =
            '<i class="fa-solid fa-star"></i> ' +
            '<b>' + gettext("First to solve") + '</b> ';
    var lastRequestId = -1;
    var fetchInterval = 5000;
    var fadeInterval = 1000;
    var errorDiv = $('.row').find('div.alert-danger');
    var createRow = function(color, team, id, isFirst, problemName) {
        var row = $(rowTemplate.replace('__TEAM__', team));
        var colorCellText = problemName;
        if (color === null) {
            colorCellText +=
                ' <small class="no-color">' + gettext("No color") +
                 '</small>';
        } else {
            $('.color-cell', row).css('background-color', color);
        }
        $('.color-cell', row).html(colorCellText);
        row.data('id', id);
        if (isFirst) {
            row.find('.team-cell').prepend(firstAcceptedTemplate);
        }
        return row;
    };
    var setDeliveryButton = function(row, buttonTemplate) {
        $('.button-cell', row).empty().append(buttonTemplate);
    };
    var appendToNotDelivered = function(row) {
        setDeliveryButton(row, deliveredButtonTemplate);
        row.hide();
        row.appendTo($('#not-delivered').find('tbody'));
        row.fadeIn(fadeInterval);
    };
    var prependToDelivered = function(row) {
        setDeliveryButton(row, notDeliveredButtonTemplate);
        if ($('#delivered tr').length > 10) {
            $('#delivered tr').last().remove();
        }
        row.hide();
        row.prependTo($('#delivered').find('tbody'));
        row.fadeIn(fadeInterval);
    };
    var hideRequestError = function() {
        errorDiv.hide();
    };
    var showRequestError = function(reason) {
        if (!reason) {
            reason = gettext('No connection');
        }
        $('span', errorDiv).text('(' + reason + ')');
        errorDiv.show();
    };
    var setButtonEvents = function(setDeliveredUrl) {
        var afterRequest = function(btn, data, moveRow) {
            if (data.result == 'ok') {
                hideRequestError();
                var row = btn.closest('tr');
                row.detach();
                moveRow(row);
            } else {
                btn.button('reset');
                showRequestError(gettext('Corrupt data'));
            }
        };
        var buttonOnclick = function(btn, newDelivered, moveRow) {
            btn.button('loading');
            var row = btn.closest('tr');
            var id = row.data('id');
            $.ajax({
                type: 'POST',
                data: {
                    id: id,
                    new_delivered: newDelivered,
                    csrfmiddlewaretoken: Cookies.get('csrftoken')
                },
                url: setDeliveredUrl,
                success: function(data) { afterRequest(btn, data, moveRow); },
                error: function(jqXHR) {
                    btn.button('reset');
                    showRequestError(jqXHR.status);
                }
            });
            return false;
        };
        $('#delivered').on('click', '.button-cell button', function() {
            return buttonOnclick($(this), 'False', appendToNotDelivered);
        });
        $('#not-delivered').on('click', '.button-cell button', function() {
            return buttonOnclick($(this), 'True', prependToDelivered);
        });
    };
    var fetchNewDeliveryRequests = function(fetch_url) {
        $.ajax({
            type: 'GET',
            data: {last_id: lastRequestId},
            url: fetch_url,
            success: function(data) {
                hideRequestError();
                lastRequestId = data.new_last_id;
                for (var i = 0; i < data.new_requests.length; ++i) {
                    var request = data.new_requests[i];
                    var newRow = createRow(request.color, request.team,
                        request.id, request.first_accepted,
                        request.problem_name);
                    appendToNotDelivered(newRow);
                }
                setTimeout(function() {
                    fetchNewDeliveryRequests(fetch_url);
                }, fetchInterval);
            },
            error: function(jqXHR) {
                showRequestError(jqXHR.status);
                setTimeout(function() {
                    fetchNewDeliveryRequests(fetch_url);
                }, fetchInterval);
            }
        });
    };

    const setDeliveredUrl = $("#set-delivered-url").val();
    const fetchUrl = $("#fetch-url").val();
    setButtonEvents(setDeliveredUrl);
    fetchNewDeliveryRequests(fetchUrl);
});
