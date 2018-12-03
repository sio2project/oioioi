/**
 * Sets up displaying number of test runs left based on current value of select.
 * @param {Object.<string,number>} submissionsLeft maps problem id to its limit
 */
function displayTestRunsLeft(submissionsLeft) {
    // Note that similar function is implemented for test runs and if you're
    // changing anything you most probably want to change it in both files.
    // The code is duplicated because of django translations which does not
    // trigger for javascript in templates (submissions have different text).
    const $message = $('#submissions-left');
    const $select = $('select#id_problem_instance_id');

    $select.change(function(e) {
        let left = submissionsLeft[this.value];
        if(left === 0 || left) {
            $message.text(
                ngettext('You have %(sub_num)s test run left.',
                         'You have %(sub_num)s test runs left.', left)
                    .fmt({sub_num: left}));
            $message.removeClass('hidden');
        }
        else // there is no limit
            $message.addClass('hidden');
    });

    $select.change(); // triggers event to set correct start message
}
