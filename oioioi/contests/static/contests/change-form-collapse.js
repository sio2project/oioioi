$(document).ready(function() {
    const buttons = document.getElementsByClassName("category-collapsible");
    const elements = document.getElementsByClassName("category-content");
    let i;

    for (i = 0; i < elements.length; i++) {
        elements[i].addEventListener("click", function () {
            this.style.maxHeight = this.scrollHeight + "px";
        });
    }

    for (i = 0; i < buttons.length; i++) {
        buttons[i].addEventListener("click", function () {
            let arrow = this.getElementsByClassName("arrow")[0]
            this.classList.toggle("active");
            arrow.classList.toggle("up")
            let content = this.nextElementSibling;
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });
    }
});
