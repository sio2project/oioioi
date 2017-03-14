function setLanguage(lang) {
    $.cookie("lang", lang, {
        expires: 7,
        path: oioioi_base_url
    });
    location.reload();
}

$(document).ready(function() {
    $(".lang-select").each(function(index, value) {
        $(value).click(function(event) {
            event.preventDefault();
            setLanguage(value.lang);
        });
    });
});
