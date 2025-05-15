function init_search_selection(id) {
    $(function(){
        const input = $('#' + id);

        // The default source - returns hints for contests
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
                if(!input.val()) {
                    return false;
                }
                return true;
            },
            updater: function(item) {
                const typeahead = input.data('typeahead');
                let result = item.search_name || item.name;

                return result;
            },
        });
    });
}
