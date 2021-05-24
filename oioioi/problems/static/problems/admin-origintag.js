/* This script narrows down the choice of OriginInfoValues to only include those
 * corresponding to some tag. This is only for user convenience - validation can
 * be done in the form.
 */
$(document).ready(function() {
    const null_option = '---------';
    const origintags = '[id^=id_OriginTag_problems-][id$=-origintag]';
    const origininfovalues = '[id^=id_OriginInfoValue_problems-][id$=-origininfovalue]';

    let on_change = function() {
        // Get currently selected origintags
        let tag_values = [];
        $(origintags).each(function() {
            tag_values.push($(this).find('option:selected').text());
        });

        // Only display origin info values corresponding to some origintag
        $(origininfovalues).each(function() {
            let value_select = $(this);
            value_select.find('option').each(function() {
                let option = $(this).text();
                let has_origintag = false;
                tag_values.forEach(function(tag_value, i, a) {
                    if (tag_value !== "" && option.startsWith(tag_value + ' ')) {
                        has_origintag = true;
                    }
                });
                if (option === null_option || has_origintag) {
                    $(this).show();
                } else {
                    $(this).hide();
                    if ($(this).val() === value_select.val()) {
                        value_select.val('');
                    }
                }
            });
            $(origininfovalues).change();
        });
    };

    // If any row gets added we need to setup a new trigger
    django.jQuery(document).on('formset:added',
                               function(event, $row, formsetName) {
        if (formsetName === 'OriginTag_problems') {
            $row.find(origintags).on('change', on_change);
        }
    });

    // If an origin tag is removed we need to recalculate possible origin meta
    django.jQuery(document).on('formset:removed',
                               function(event, $row, formsetName) {
        if (formsetName === 'OriginTag_problems') {
            on_change();
        }
    });

    // Setup triggers and calculate initial values
    $(origintags).on('change', on_change);
    on_change();

    // Trigger change events when Django admin's popup window is dismissed
    // Based on: https://stackoverflow.com/a/33937138

    function triggerChangeOnField(win) {
        const name = windowname_to_id(win.name);
        const elem = document.getElementById(name);
        $(elem).change();
    }

    window.dismissChangeRelatedObjectPopup = function(fn) {
        return function(win, objId, newRepr, newId) {
            fn(win, objId, newRepr, newId);
            triggerChangeOnField(win);
        };
    } (window.dismissChangeRelatedObjectPopup);

    window.dismissAddRelatedObjectPopup = function(fn) {
        return function(win, newId, newRepr) {
            fn(win, newId, newRepr);
            triggerChangeOnField(win);
        };
    } (window.dismissAddRelatedObjectPopup);
});
