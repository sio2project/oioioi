var Attachments = (function() {
    "use strict";

    var Attachments = function() {
        this.new_attachment_row_html =
            /*jshint multistr: true */
            '<tr class="newly-added"> \
                <td> \
                    <input type="file" name="attachment-xxx-content" /> \
                </td> \
                <td> \
                    <input type="text" name="attachment-xxx-description" /> \
                </td> \
                <td> \
                    <a href="#" class="delete_attachment newly_added">\
                        ' + gettext("Delete") + ' \
                    </a> \
                </td> \
            </tr>';
    };

    Attachments.prototype.bindActions = function() {
        var _this = this;

        $(document).on('click', '.delete_attachment', function(e) {
            e.preventDefault();
            _this._deleteAttachment($(this));
        });

        $(document).on('click', '.create_attachment', function(e) {
            e.preventDefault();
            _this._createAttachment();
        });
    };

    Attachments.prototype._deleteAttachment = function(attachment) {
        var tableRow = attachment.closest('tr');

        var localOnly = attachment.hasClass('newly_added')
            || tableRow.find('input[type=text]').length > 0;

        if (localOnly) {
            var current_row = tableRow.next();

            // Last child is row with new inputs, which is NOT part of the
            // formset.
            while (!current_row.is(':last-child')) {
                var file_input = current_row.find('input[type=file]');
                var description_input = current_row.find('input[type=text]');

                // Modify index within the formset.
                var fileIndex = parseInt(
                    file_input.attr('name').split('-')[1]
                );

                var descriptionIndex = parseInt(
                    description_input.attr('name').split('-')[1]
                );

                file_input.attr(
                    'name',
                    'attachment-' + (fileIndex - 1) + '-content'
                );

                description_input.attr(
                    'name',
                    'attachment-' + (descriptionIndex - 1) + '-description'
                );

                current_row = current_row.next();
            }

            tableRow.remove();

            // Update form count in the formset.
            $('#id_attachment-TOTAL_FORMS').val(
                parseInt($('#id_attachment-TOTAL_FORMS').val()) - 1
            );
        } else {
            var current_id = attachment.parent().prev().find('input')
                .attr('name').split('-')[1];

            $('#main_form').append(
                '<input type="hidden" ' +
                'name="attachment-' + current_id + '-DELETE" value="on" />'
            );

            tableRow.addClass("to-be-deleted");
        }
    };

    Attachments.prototype._createAttachment = function() {
        var current_id = parseInt($('#id_attachment-TOTAL_FORMS').val()) - 1;
        var next_id = current_id + 1;
        var new_row = this.new_attachment_row_html;
        var re = new RegExp('xxx', 'g');
        new_row = new_row.replace(re, next_id);
        $('#id_attachment-TOTAL_FORMS').val(next_id + 1);
        $('#attachment_table').find('tbody').children().last().before(new_row);

        // File fields cannot be set using the val() function because of
        // security issues.Because of that, we're copying the input and then
        // swapping name attributes.
        var new_attachment_file = $('#new_attachment_file');

        // The one added with the .before(new_row) call a few lines before.
        // It doesn't contain the file and it will not. It serves only as a
        // container of name attributes.
        var original = $('#attachment_table').find('tbody').children().last()
            .prev().find('input[type=file]');
        original.after(new_attachment_file);
        new_attachment_file.removeAttr('id');
        new_attachment_file.attr('name', original.attr('name'));
        original.remove();

        // We've moved the input and need to add it again.
        $('#new_attachment_row').find('td').first().html(
            '<input type="file" id="new_attachment_file" />'
        );

        // Update the description.
        $('#attachment_table').find('tbody').children().last().prev()
            .find('input[type=text]').val($('#new_attachment_description')
            .val());

        $('#new_attachment_description').val('');
    };

    return Attachments;
}());