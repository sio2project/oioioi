var Tags = (function() {
    "use strict";

    var Tags = function() {
        this.new_tag_row_html =
            /*jshint multistr: true */
            '<tr class="newly_added"> \
                <td> \
                    <input type="text" name="tag-xxx-name" /> \
                </td> \
                <td> \
                    <a href="#" class="delete_tag newly_added">\
                        ' + gettext("Delete") + ' \
                    </a> \
                </td> \
            </tr>';
    };

    Tags.prototype.bindActions = function() {
        var _this = this;

        $(document).on('click', '.delete_tag', function(e) {
            e.preventDefault();
            _this._deleteTag($(this));
        });

        $(document).on('click', '.create_tag', function(e) {
            e.preventDefault();
            _this._createTag();
        });
    };

    Tags.prototype._deleteTag = function(tag) {
        var tableRow = tag.closest('tr');

        var localOnly = tag.hasClass('newly_added')
            || tableRow.find('input[type=text]').length > 0;

        if (localOnly) {
            var current_row = tableRow.next();

            // Last child is row with new inputs, which is NOT part of the
            // formset.
            while (!current_row.is(':last-child')) {
                if (!current_row.hasClass('newly_added')) {
                    var description_input = current_row.find(
                        'input[type=text]');

                    // Modify index within the formset.
                    var oldIndex = parseInt(
                        description_input.attr('name').split('-')[1]
                    );

                    description_input.attr(
                        'name',
                        'tag-' + (oldIndex - 1) + '-name'
                    );
                }

                current_row = current_row.next();
            }

            tableRow.remove();

            // Update form count in the formset.
            $('#id_tag-TOTAL_FORMS').val(
                parseInt($('#id_tag-TOTAL_FORMS').val()) - 1
            );
        } else {
            var current_id = tag.parent().prev().find('input').attr('name')
                .split('-')[1];

            $('#main_form').append(
                '<input type="hidden" name="tag-' + current_id + '-DELETE" ' +
                'value="on" />'
            );

            tableRow.addClass("to-be-deleted");
        }
    };

    Tags.prototype._createTag = function() {
        var current_id = parseInt($('#id_tag-TOTAL_FORMS').val()) - 1;
        var next_id = current_id + 1;
        var new_row = this.new_tag_row_html;
        var re = new RegExp('xxx', 'g');
        new_row = new_row.replace(re, next_id);

        $('#id_tag-TOTAL_FORMS').val(next_id + 1);

        $('#tag_table').find('tbody').children().last().before(new_row);
        $('#tag_table').find('tbody').children().last().prev().find('input')
            .val($('#new_tag_name').val());
        $('#new_tag_name').val('');
    };

    return Tags;
}());