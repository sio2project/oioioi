/* Inititates DateTimePicker widgets
 * for use with oioioi.base.widgets.DateTimePicker
 */
$(document).ready(function() {
    $(".datetimepicker").datetimepicker({
        format: 'yyyy-MM-dd hh:mm',
        langugage: '{{ LANGUAGE_CODE|default:"en" }}',
        pickSeconds: false
    });
});
