function performActionAfterTooltipCloses(el, fn) {

    const tooltipId = el.getAttribute("aria-describedby");
    const tooltipEl = document.getElementById(tooltipId);

    const observer = new MutationObserver(function (records) {
        const removedEls = Array.from(records.pop().removedNodes);
        if (removedEls.includes(tooltipEl)) {
            fn();
            observer.disconnect();
        }
    });
    observer.observe(tooltipEl.parentElement, {attributes: false, childList: true});
}

function createLink(link) {
    const url = new URL(window.location.href);
    url.hash = link;
    return url.toString();
}

function showMessage(el) {
    const prevTitle = el.dataset.originalTitle;

    el.setAttribute('data-bs-original-title', 'Copied link!');
    const tooltip = bootstrap.Tooltip.getInstance(el);
    tooltip.show();

    const restoreTitle = () => {
        el.setAttribute('data-bs-original-title', prevTitle);
        tooltip.hide();
    };

    setTimeout(function () {
        performActionAfterTooltipCloses(el, restoreTitle);
    }, 0);

}

function copyLink(link) {
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.type = "text";
    input.value = link;

    // https://www.w3schools.com/howto/howto_js_copy_clipboard.asp

    // Select the text field
    input.select();
    input.setSelectionRange(0, 99999);  // To ensure mobile devices compatibility,
    // we use setSelectionRange instead select().
    // selectionEnd value is chosen to be big enough to store any possible input.

    /* Copy the text inside the text field */
    document.execCommand("copy");
    document.body.removeChild(input);
}

function enableCopy() {
    $(document).on('click', '.link-getter', function () {
        const link = createLink(this.dataset.link);
        copyLink(link);
        location.replace(link);
        showMessage(this);
    });
}

function chooseActive() {
    const hash = location.hash;

    if (hash) {
        const el = document.querySelector('a[href="' + hash + '"]');
        if (el) {
            el.click();
        }
    }
}

function initLinks() {
    chooseActive();
    enableCopy();
}

window.onload = initLinks;

