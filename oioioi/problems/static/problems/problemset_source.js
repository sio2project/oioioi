$(document).ready(function(){
    // Prepare secret key form unhide
    $('#show-secret-key').click(function(){
        $('#secret-key-form-more').show(500);
    });

    // Prevent form from submitting more than once
    $('form.submit-once').submit(function(e){
        if($(this).hasClass('form-submitted')){
            e.preventDefault();
            return;
        }
        $(this).addClass('form-submitted');
        $('#secret-key-submit').addClass('long-job-active');
    });
});