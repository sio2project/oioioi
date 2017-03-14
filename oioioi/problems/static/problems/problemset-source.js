$(document).ready(function() {
    const secretKeyForm = $('#secret-key-form');
    const secretKeyShow = $('#secret-key-show');
    const secretKeySubmit = $('#secret-key-submit');

    secretKeyForm.hide();

    // Prepare secret key form unhide
    secretKeyShow.click(function() {
        secretKeyForm.show(500);
    });

    // Prevent form from submitting more than once
    secretKeyForm.submit(function(event) {
        if ($(this).hasClass('form-submitted')) {
            event.preventDefault();
            return;
        }
        $(this).addClass('form-submitted');
        secretKeySubmit.addClass('long-job-active');
    });
});