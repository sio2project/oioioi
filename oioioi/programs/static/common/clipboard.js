function copyCodeToClipboard() {
    navigator.clipboard.writeText(document.getElementById("raw_source").textContent).then(function() {
        const button = document.getElementById("cpy_btn");
        button.classList.add("btn-success");
        button.textContent = "Copied!";
    }, function() {
        alert("Unable to copy Code");
    });
}
