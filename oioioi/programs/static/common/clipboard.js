function successCopy() {
    const button = document.getElementById("cpy_btn");
    button.classList.remove("btn-outline-secondary");
    button.classList.add("btn-success");
    button.textContent = gettext("Copied!");
}

function failCopy() {
    alert(gettext("Unable to copy Code"));
}

function copyCodeToClipboard() {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(
            document.getElementById("raw_source").textContent
        ).then(
            successCopy,
            failCopy
        );
    }
    else {
        const textArea = document.createElement("textarea");
        // Hide the textArea from view
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        textArea.value = document.getElementById("raw_source").textContent;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand("copy");
            successCopy();
        } catch (err) {
            failCopy();
        }
        document.body.removeChild(textArea);
    }
}
