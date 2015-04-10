function enableUserLookupForm(formSelector, failFunc) {
    var form = $(formSelector);
    var input_username = form.children('input[name=\'username\']');

    var query_url = form.attr('data-check-url');

    form.submit(function(event) {
        var username = input_username.val();

        $.ajax(query_url, {
            contentType: 'text/plain',
            data: {username: username}
        }).done(function(data) {
            if (data.userExists) {
                window.location.href = data.profileUrl;
            } else {
                failFunc(username);
            }
        });

        event.preventDefault();
    });
}
