$(document).ready(function () {

    const selectedColor = 'lightgreen';
    const unselectedColor = '#e5e5e5';

    const $modalFooter = $('.modal-footer');
    const $submittedText = $('#after-submission');
    const $form = $('#tag-form');
    const $buttons = $('.btn-option');
    const $formOpen = $('#open-form');
    const $algorithmInput = $('#algorithm-tags');
    const $autocomplete = $('#autocomplete');
    const $proposals = $('#tags-container');
    const $inputContainer = $('.tag-input');
    const $submit = $('#submit');
    const $serverError = $('#server-error');
    const $invalidForm = $('#invalid-form');

    function clearAutocomplete() {
        var $list = $('.autocomplete-list');
        $list.children().remove();
        $list.remove();
    }

    function clearActive() {
        var $items = $('.autocomplete-active');
        $items.removeClass('autocomplete-active');
    }

    function clearProposals() {
        $proposals.empty();
        $proposals.addClass("hidden");
        $inputContainer.css('margin-bottom', '4rem');
    }

    // enable tooltips
    $('[data-toggle="tooltip"]').tooltip();

    // show tag proposal form to the user if it's the first time they qualify
    if ($formOpen.length && !$.cookie('shown_proposal_popup')) {
        $form.modal('toggle');
        $.cookie('shown_proposal_popup', true, { expires: 1000 });
    }

    // allow only one button to be selected
    $buttons.on('click', function () {
        $buttons.css('background-color', unselectedColor);
        $buttons.attr('data-state', '');
        $(this).css('background-color', selectedColor);
        $(this).attr('data-state', 'selected');
    });

    // add hovering
    $buttons.hover(function () {
        $(this).css('background-color', selectedColor);
    }, function () {
        if ($(this).attr('data-state') != 'selected') {
            $(this).css('background-color', unselectedColor);
        }
    });

    // clear the form every time it opens
    $formOpen.on('click', function () {
        $algorithmInput.val('');
        $buttons.css('background-color', unselectedColor);
        $buttons.attr('data-state', '');
        $serverError.addClass('hidden');
        $invalidForm.addClass('hidden');
        clearProposals();
    });

    // autocomplete tags
    $algorithmInput.on('input', function () {
        var val = $(this).val();

        clearAutocomplete();

        if (val != "") {

            var url = $(this).data('hintsUrl');
            $.getJSON(url, {query: val}).done(function (hints) {
                var possibleTags = hints.filter(function (hint) {
                    var add = true;
                    $('.tag-proposal').each(function () {
                        if ($(this).text() == hint) {
                            add = false;
                        }
                    });
                    return add;
                }).map(function (hint) {
                    return '<li class="autocomplete-item"><strong>' + hint.substring(0, val.length) +
                        '</strong>' + hint.substring(val.length) + '</li>';
                });

                $autocomplete.append('<ul class="autocomplete-list"></ul>');
                $('.autocomplete-list').append(possibleTags);
            });

        }
    });

    // mouse hovering for autocomplete options
    $autocomplete.on('mouseenter', '.autocomplete-item', function () {
        clearActive();
        $(this).addClass('autocomplete-active');
    });

    // autofill when clicked
    $autocomplete.on('click', '.autocomplete-item', function () {
        $algorithmInput.val($(this).text());
        clearAutocomplete();
    });

    // close autocomplete when clicked anywhere else on the document
    $(document).on('click', function () {
        clearAutocomplete();
    });

    // handle keyboard navigation
    $algorithmInput.on('keydown', function (e) {
        var $items = $('.autocomplete-item');
        var $active = $('.autocomplete-active');

        switch (e.which) {

            // down
            case 40:
                if (!$active.length) {
                    $items.first().addClass('autocomplete-active');
                } else {
                    $active.removeClass('autocomplete-active');
                    $active.next().addClass('autocomplete-active');
                }
                break;

            // up
            case 38:
                if ($active.length) {
                    $active.removeClass('autocomplete-active');
                    $active.prev().addClass('autocomplete-active');
                } else {
                    $items.last().addClass('autocomplete-active');
                }
                break;

            // enter
            case 13:
                e.preventDefault();
                if ($active.length) {
                    $active.click();
                } else {
                    var url = $(this).data('taglabelUrl');
                    var name = $algorithmInput.val();
                    var proposed = $('.tag-proposal').toArray().map(function (proposal) {
                        return proposal.textContent;
                    });
                    $.getJSON(url, {name: name, proposed: jQuery.inArray(name, proposed)}).done(function (tag) {
                        $inputContainer.css('margin-bottom', '2rem');
                        var label = $('<span/>', {
                            'class': 'label tag-label tag-proposal tag-label-algorithm',
                            text: tag,
                        });
                        $proposals.append(label);
                        $proposals.append('\n');
                        $proposals.removeClass('hidden');
                        $algorithmInput.val('');
                    });
                }

        }
    });

    // deleting proposals
    $proposals.on('click', '.tag-proposal', function () {
       $(this).remove();
       if (!$proposals.children().length) {
           $proposals.addClass('hidden');
           $inputContainer.css('margin-bottom', '4rem');
       }
    });

    // post data after submit
    $submit.on('click', function () {
        var tags = $('.tag-proposal').toArray().map(function (proposal) {
            return proposal.textContent;
        });
        var difficulty = '';
        const $selected = $('button[data-state="selected"]');
        if ($selected.length) {
            difficulty = $selected.toArray()[0].textContent;
        }

        $serverError.addClass('hidden');
        $invalidForm.addClass('hidden');

        if (!tags.length) {
            $invalidForm.removeClass('hidden');
            return;
        }

        var proposals = {
            tags: tags,
            difficulty: difficulty,
            problem: $(this).data('problem'),
            user: $(this).data('user'),
            csrfmiddlewaretoken: $.cookie('csrftoken'),
        };

        $.ajax({
            type: 'POST',
            url: $(this).data('submitUrl'),
            data: proposals,
            success: function () {
                $modalFooter.remove();
                $submittedText.siblings().remove();
                $submittedText.removeClass('hidden');
                $form.modal('toggle');
            },
            error: function () {
                $serverError.removeClass('hidden');
            }
        });
    });

});

