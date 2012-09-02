function set_lang(lang) {
    return function() {
        $.cookie("lang", lang, { expires: 7, path: oioioi_base_url });
        location.reload();
    };
}

$(document).ready(function() {
    $("#lang_list img").each(function(i, v){ $(v).click(set_lang(v.lang));} );
});
