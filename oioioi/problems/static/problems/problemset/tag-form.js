$(document).ready(function () {
    const selectedColor = 'lightgreen';
    const unselectedColor = '#e5e5e5';

    const $modalFooter = $('.modal-footer');
    const $submittedText = $('#after-submission');
    const $form = $('#tag-form');
    const $buttons = $('.btn-option');
    const $formOpen = $('#open-form');
    const $algorithmInput = $('#algorithm-tags');
    const $addAlgorithm = $('#add-algorithm');
    const $autocomplete = $('#autocomplete');
    const $proposals = $('#tags-container');
    const $inputContainer = $('.tag-input');
    const $submit = $('#submit');
    const $serverError = $('#server-error');
    const $invalidForm = $('#invalid-form');

    function clearAutocomplete() {
        const $list = $('.autocomplete-list');
        $list.children().remove();
        $list.remove();
    }

    function clearActive() {
        const $items = $('.autocomplete-active');
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
    if ($formOpen.length && !Cookies.get('shown_proposal_popup')) {
        $form.modal('toggle');
        Cookies.set('shown_proposal_popup', true, { expires: 1000 });
    }

    // allow only one button to be selected
    $buttons.on('click', function () {
        const prevDataState = $(this).attr('data-state');
        $buttons.css('background-color', unselectedColor);
        $buttons.attr('data-state', '');
        if (prevDataState !== 'selected') {
            $(this).css('background-color', selectedColor);
            $(this).attr('data-state', 'selected');
        }
    });

    // add hovering
    $buttons.hover(function () {
        $(this).css('background-color', selectedColor);
    }, function () {
        if ($(this).attr('data-state') !== 'selected') {
            $(this).css('background-color', unselectedColor);
        }
    });

    // clear the form every time it opens
    $formOpen.on('click', function () {
        $algorithmInput.val('');
        $addAlgorithm.attr('disabled', true);
        $buttons.css('background-color', unselectedColor);
        $buttons.attr('data-state', '');
        $serverError.addClass('hidden');
        $invalidForm.addClass('hidden');
        clearProposals();
    });

    // autocomplete tags
    $algorithmInput.on('input', function () {
        const val = $(this).val();

        clearAutocomplete();

        if (val !== "") {
            const url = $(this).data('hintsUrl');
            $.getJSON(url, {query: val}).done(function (hints) {
                const possibleTags = hints.filter(function (hint) {
                    let add = true;
                    $('.tag-proposal').each(function () {
                        if ($(this).text() === hint) {
                            add = false;
                        }
                    });

                    return add;
                }).map(function (hint) {
                    const occurrence = hint.toLowerCase().indexOf(val.toLowerCase());
                    if (occurrence !== -1) {
                        const beforeBold = hint.substring(0, occurrence);
                        const bold = hint.substring(occurrence, occurrence + val.length);
                        const afterBold = hint.substring(occurrence + val.length);
                        hint = `${beforeBold}<strong>${bold}</strong>${afterBold}`;
                    }

                    return `<li class="autocomplete-item">${hint}</li>`;
                });

                $autocomplete.append('<ul class="autocomplete-list"></ul>');
                $('.autocomplete-list').append(possibleTags);
            });
        } else {
             $addAlgorithm.attr('disabled', true);
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
        $addAlgorithm.removeAttr('disabled');
        clearAutocomplete();
    });

    // close autocomplete when clicked anywhere else on the document
    $(document).on('click', function () {
        clearAutocomplete();
    });

    // function invoked when hitting enter when focus on text input is on
    // or when clicking "Add" button if enabled
    function addTagLabel(tagLabelUrl) {
        const name = $algorithmInput.val();
        const proposed = $('.tag-proposal').toArray().map(function (proposal) {
            return proposal.textContent;
        });
        $.getJSON(tagLabelUrl, {name: name, proposed: jQuery.inArray(name, proposed)}).done(function (tags) {
            tags.forEach(function (tag) {
                $inputContainer.css('margin-bottom', '2rem');
                const label = $('<span/>', {
                    'class': 'label tag-label tag-proposal tag-label-algorithm',
                    text: tag,
                });
                $proposals.append(label);
                $proposals.append('\n');
                $proposals.removeClass('hidden');
                $algorithmInput.val('');
                $addAlgorithm.attr('disabled', true);
            });
        });
    }

    // handle keyboard navigation
    $algorithmInput.on('keydown', function (e) {
        const $items = $('.autocomplete-item');
        const $active = $('.autocomplete-active');

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
                    addTagLabel($(this).data('taglabelUrl'));
                }
        }
    });

    // adding algorithms using "Add" button
    $addAlgorithm.on('click', function () {
        addTagLabel($(this).data('taglabelUrl'));
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
        const tags = $('.tag-proposal').toArray().map(function (proposal) {
            return proposal.textContent;
        });
        let difficulty = '';
        const $selected = $('button[data-state="selected"]');
        if ($selected.length) {
            difficulty = $selected.toArray()[0].textContent.trim();
        }

        $serverError.addClass('hidden');
        $invalidForm.addClass('hidden');

        if (!tags.length || difficulty === '') {
            $invalidForm.removeClass('hidden');
            return;
        }

        const proposals = {
            tags: tags,
            difficulty: difficulty,
            problem: $(this).data('problem'),
            user: $(this).data('user'),
            csrfmiddlewaretoken: Cookies.get('csrftoken'),
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
