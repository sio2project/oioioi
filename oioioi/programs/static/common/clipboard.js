function copyCodeToClipboard() {
    navigator.clipboard.writeText(document.getElementById("raw_source").textContent).then(function() {
        const button = document.getElementById("cpy_btn");
        button.classList.remove("btn-outline-secondary");
        button.classList.add("btn-success");
        button.textContent = gettext("Copied!");
    }, function() {
        alert(gettext("Unable to copy Code"));
    });
}
