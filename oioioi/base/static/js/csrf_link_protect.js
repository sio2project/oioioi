$(document).ready(function() {
    $('body').on('click', '[data-post-url]', function(event) {
        var data = $(this).data();
        var form = $('<form method="post"></form>');
        form.attr('action', data.postUrl);
        for (var name in data) {
            if (typeof name == "string" && name.startsWith('postField')) {
                var field_name = name.replace(/^postField/,'').replace(
                        /([a-z])([A-Z])/g, '$1-$2').toLowerCase();
                form.append($('<input type="hidden"></input>').attr('name',
                        field_name).val(data[name]));
            }
        }
        form.append($('<input type="hidden"></input>').attr('name',
                'csrfmiddlewaretoken').val(Cookies.get("csrftoken")));
        form.appendTo('body').submit();
        event.preventDefault();
    });
});
