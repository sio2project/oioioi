function setLanguage(lang) {
    Cookies.set("lang", lang, {
        expires: 7,
        path: oioioi_base_url
    });
    location.reload();
}

$(() => {
    $(".lang-select").each((index, value) => {
        $(value).on("click", (event) => {
            event.preventDefault();
            setLanguage(value.lang);
        });
    });
});
