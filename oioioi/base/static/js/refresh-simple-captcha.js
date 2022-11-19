// See https://django-simple-captcha.readthedocs.io/en/latest/usage.html#example-usage-ajax-refresh-button
$(function() {

    // Click-handler for the play button
    $('.js-captcha-play-audio').click(function () {
        const $form = $(this).parents('form');
        $form.find('#audio').get(0).play();
    });

    // Click-handler for the refresh button
    $('.js-captcha-refresh').click(function(){
        const $form = $(this).parents('form');
        const url = location.protocol + "//" + window.location.hostname + ":"
            + location.port + "/captcha/refresh/";

        $.getJSON(url, {}, function(result_json) {
            $form.find('input[name="captcha_0"]').val(result_json.key);
            $form.find('img.captcha').attr('src', result_json.image_url);
            const audio = $form.find('#audio');
            audio.attr('src', result_json.audio_url);
            audio.get(0).load();
        });
    });

    return false;
});
