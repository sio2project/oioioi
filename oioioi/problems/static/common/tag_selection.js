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

function init_tag_selection(id) {
    $(function(){
        var input = $('#' + id);
        var form = $('#' + id + '-form');
        input.typeahead({
            source: function(query, process) {
                $.getJSON(input.data("hintsUrl"), {substr: query}, process);
            },
            minLength: 2,
            updater: function(item) {
                input.val(item);
                form.submit();
                return item;
            },
        });
    });
}
