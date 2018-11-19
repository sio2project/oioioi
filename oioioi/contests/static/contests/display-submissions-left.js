const $message = $('#submissions-left');
const $select = $('select#id_problem_instance_id');

$select.change(function(e) {
    let left = submissionsLeft[this.value];
    if(left === 0 || left) {
        $message.text(
            ngettext('You have %(sub_num)s submission left.',
                     'You have %(sub_num)s submissions left.', left)
                .fmt({sub_num: left}));
        $message.removeClass('hidden');
    }
    else // there is no limit
        $message.addClass('hidden');
});

$select.change(); // triggers event to set correct start message
