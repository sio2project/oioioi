function init_tag_addition(id, hints_url) {
    $(function(){
        var input = $('#' + id);
        var hints = $('#' + id + '-hints');

        /* Prevent multiple-initialization */
        if(input.data("init"))
            return;
        input.data("init", true);

        var changeInput = function() {
            var make_hint = function(tag, query) {
                var index = tag.indexOf(query);
                var pre = tag.substr(0, index);
                var mid = tag.substr(index, query.length);
                var suf = tag.substr(index + query.length);

                var label = $("<strong></strong>");
                label.html(pre + "<u>" + mid + "</u>" + suf);
                label.click(function() { input.val(tag); changeInput(); });
                label.css('cursor', 'pointer');
                return label;
            };

            var html_escape = function(str) {
                return String(str)
                    .replace(/&/g, '&amp;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
            };

            var query = input.val();

            if(query.length >= 2) {
                $.getJSON(hints_url, {substr: query},
                    function(items) {
                        var exists = false;
                        var hint_chain = $('<span></span>');
                        var count = 0;
                        for(var i = 0; i < items.length; i++) {
                            if(items[i] == query)
                                exists = true;
                            else {
                                if(count !== 0)
                                    hint_chain.append(", ");
                                else
                                    hint_chain.append(gettext("Try: "));
                                hint_chain.append(make_hint(items[i], query));
                                count++;
                            }
                        }
                        if(!exists) {
                            hints.html(gettext(
                                "Tag '%(query)s' doesn't exist." +
                                " It will be added if you save the problem.")
                                    .fmt({query: html_escape(query)}) + " ");
                        } else {
                            hints.html(gettext("Tag exists.") + " ");
                        }
                        hints.append(hint_chain);
                    });
            } else {
                hints.html(gettext("Type tag name."));
            }
        };

        input.keyup(changeInput);
        input.change(changeInput);

        changeInput();
    });
}

function add_search_tag(parent_node, key, value, text) {
    var node = $('.search-tag-root').first().clone(true);
    node.find('.label')
        .removeClass('tag-label-')
        .addClass('tag-label-' + key);
    node.find('input')
        .prop('disabled', false)
        .prop('readonly', true)
        .prop('name', key)
        .val(value);
    node.find('.search-tag-text')
        .text(text || value);
    node.appendTo(parent_node).show();
    return node;
}

function init_search_selection(id) {
    $(function(){
        var input = $('#' + id);

        // The default source - returns hints for all tags and problems.
        var source_default = function(query, process) {
            $.getJSON(input.data("hintsUrl"), {q: query}, process);
        };

        input.typeahead({
            source: source_default,
            minLength: 2,
            fitToElement: true,
            autoSelect: false,
            matcher: function(item) {
                // Bug fix: backspace on empty input matched last results.
                if( !input.val() )
                    return false;

                // Every item returned by the hints url should have already
                // been matched in python code.
                return true;
            },
            updater: function(item) {
                // We may want to change the selection pool.
                var typeahead = input.data('typeahead');

                // We also need to return a string to be put in the search box.
                // Sometimes we will be forcing the search menu to reload
                // immediately instead of just accepting a value - this can be
                // done by by calling the typeahead.lookup() method.
                // In such case the input box value has to be updated manually.
                var result = item.search_name || item.name;

                if (item.trigger == "origintag-menu") {
                    // When the search only matches one origintag, the hints url
                    // will return its categories too. This trigger is to help a
                    // user choose to match a particular tag only. Reloading the
                    // menu immediately will show the categories.
                    input.val(result);
                    typeahead.lookup();

                } else if (item.trigger == "category-menu") {
                    // This trigger is to change the hints source to a specific
                    // tag's specific category's values instead of everything.
                    var source_origincategory = function(query, process) {
                        if (!query.startsWith(result)) {
                            // Reset source if prefix is removed
                            typeahead.autoSelect = false;
                            typeahead.setSource(source_default);
                            typeahead.source(query, process);
                        } else {
                            $.getJSON(input.data("origininfocategoryHintsUrl"),
                                      { category: item.value, q: query },
                                      process);
                        }
                    };
                    // Temporarily enable autoselect, since we will be reloading
                    // the menu and want it to stay selected.
                    typeahead.autoSelect = true;
                    // Reload menu immediately with source for this category.
                    typeahead.setSource(source_origincategory);
                    input.val(result);
                    typeahead.lookup();

                } else if (item.trigger != 'problem') {
                    // At this point for anything other than a problem we
                    // want to create a search tag
                    var value = item.value || item.name;

                    // Only create new search tag if it doesn't exist yet
                    var tag = $(".search-tag-text:contains('" + value + "')")
                    if (tag.length == 0) {
                        var origintag = value.split('_')[0];

                        // Make sure OriginInfo is after its OriginTag
                        var parent_node = $('#tag-row');
                        if (item.trigger && item.trigger.startsWith('origin')) {
                            group_node = $('#origintag-group-' + origintag);
                            if (group_node.length == 0) {
                                group_node = $('<div>', {
                                            'id': 'origintag-group-' + origintag,
                                            'class': 'origintag-group',
                                        }).appendTo(parent_node);

                                add_search_tag(group_node, 'origin', origintag)
                                    .click(function() {
                                        group_node.remove();
                                    });
                            }
                            parent_node = group_node;
                        }

                        // OriginTag node already has a trigger
                        if (item.trigger != 'origintag') {
                            var text = value;
                            if (item.trigger == 'origininfo')
                                text = value.split('_')[1];
                            var node = add_search_tag(parent_node, item.prefix,
                                                      value, text);
                            node.find('.search-tag-remove').click(function() {
                                node.remove();
                            });
                        }
                    }
                    // Reset source and typeahead
                    typeahead.autoSelect = false;
                    typeahead.setSource(source_default);
                    result = "";
                }
                return result;
            },
        });
    });
}
