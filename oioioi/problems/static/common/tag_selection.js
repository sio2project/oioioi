function add_search_tag(parent_node, key, value, text) {
    const node = $('.search-tag-root').first().clone(true);
    node.find('.badge')
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

function make_source_function(
    result, typeahead, source_default, input, hintsUrl, category=''
) {
    return function(query, process) {
        if (!query.startsWith(result)) {
            typeahead.autoSelect = false;
            typeahead.setSource(source_default);
            typeahead.source(query, process);
        } else {
            $.getJSON(
                input.data(hintsUrl),
                {category: category, q: query},
                process
            );
        }
    };
}

function enable_autoselect_and_reload_menu(
    typeahead, source_function, input, result
) {
    // Temporarily enable autoselect, since we will be reloading
    // the menu and want it to stay selected.
    typeahead.autoSelect = true;
    // Reload menu immediately with source for this category.
    typeahead.setSource(source_function);
    input.val(result);
    typeahead.lookup();
}

function init_search_selection(id) {
    $(function(){
        const input = $('#' + id);

        // The default source - returns hints for all tags and problems.
        const source_default = function(query, process) {
            $.getJSON(input.data("hintsUrl"), {q: query}, process);
        };

        input.typeahead({
            source: source_default,
            minLength: 2,
            fitToElement: true,
            autoSelect: false,
            followLinkOnSelect: true,
            itemLink: function(item) {
                return item.url;
            },
            matcher: function(item) {
                // Bug fix: backspace on empty input matched last results.
                if(!input.val()) {
                    return false;
                }

                // Every item returned by the hints url should have already
                // been matched in python code.
                return true;
            },
            updater: function(item) {
                // We may want to change the selection pool.
                const typeahead = input.data('typeahead');

                // We also need to return a string to be put in the search box.
                // Sometimes we will be forcing the search menu to reload
                // immediately instead of just accepting a value - this can be
                // done by by calling the typeahead.lookup() method.
                // In such case the input box value has to be updated manually.
                let result = item.search_name || item.name;

                if (item.trigger === "origintag-menu") {
                    // When the search only matches one origintag, the hints url
                    // will return its categories too. This trigger is to help a
                    // user choose to match a particular tag only. Reloading the
                    // menu immediately will show the categories.
                    const source_origintag = make_source_function(
                        result,
                        typeahead,
                        source_default,
                        input,
                        "selectedOriginTagHintsUrl"
                    );
                    enable_autoselect_and_reload_menu(
                        typeahead, source_origintag, input, result
                    );
                } else if (item.trigger === "category-menu") {
                    // This trigger is to change the hints source to a specific
                    // tag's specific category's values instead of everything.
                    const source_origincategory = make_source_function(
                        result,
                        typeahead,
                        source_default,
                        input,
                        "origininfocategoryHintsUrl",
                        item.value
                    );
                    enable_autoselect_and_reload_menu(
                        typeahead, source_origincategory, input, result
                    );
                } else if (item.trigger !== 'problem') {
                    // At this point for anything other than a problem we
                    // want to create a search tag
                    const value = item.value;

                    // Only create new search tag if it doesn't exist yet
                    const tag = $("input[name='" + item.prefix + "'][value='" + value + "']");
                    if (tag.length === 0) {
                        const tag = value.split('_')[0];

                        // Make sure OriginInfo is after its OriginTag
                        let parent_node = $('#tag-row');
                        if (item.trigger && item.trigger.startsWith('origin')) {
                            group_node = $('#origintag-group-' + tag);
                            if (group_node.length === 0) {
                                group_node = $(
                                    '<div>',
                                    {
                                        'id': 'origintag-group-' + tag,
                                        'class': 'origintag-group',
                                    }
                                ).appendTo(parent_node);

                                add_search_tag(group_node, 'origin', tag)
                                    .click(function() {
                                        group_node.remove();
                                    });
                            }
                            parent_node = group_node;
                        }

                        // OriginTag node already has a trigger
                        if (item.trigger !== 'origintag') {
                            let text = value;
                            if (item.trigger === 'origininfo') {
                                text = value.split('_')[1];
                            } else if (item.trigger === 'difficulty') {
                                text = item.name;
                            }

                            const node = add_search_tag(
                                parent_node, item.prefix, value, text
                            );
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
