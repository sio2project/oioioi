$(function () {
    // Keep this above the 0.16s grid-template-rows transition. visibility:collapse
    // drops the empty row, so it must wait until the panel has finished closing.
    const COLLAPSE_VISIBILITY_DELAY_MS = 200;

    function setExpandAllState($report) {
        const $btn = $report.find(".test-feedback-expand-all");
        if (!$btn.length) {
            return;
        }
        const $toggles = $report.find(".test-feedback-toggle");
        const allOpen = $toggles.length > 0 && $toggles.filter('[aria-expanded="true"]').length === $toggles.length;
        $btn.attr("data-expanded", allOpen ? "true" : "false");
        $btn.find(".test-feedback-expand-all-label").text(
            allOpen ? $btn.attr("data-label-collapse") : $btn.attr("data-label-expand")
        );
        $btn.find("i").toggleClass("fa-chevron-up", allOpen).toggleClass("fa-chevron-down", !allOpen);
    }

    function setFeedbackOpen($toggle, open) {
        const $panel = $($toggle.attr("data-feedback-target"));
        const $row = $panel.closest("tr");
        if (!$panel.length) {
            return;
        }
        $toggle.attr("aria-expanded", open ? "true" : "false");
        clearTimeout($row.data("collapseTimer"));
        if (open) {
            $row.removeClass("is-collapsed");
            // Force a reflow so the 0fr → 1fr transition starts from a closed row.
            $panel[0].offsetHeight;
            $panel.addClass("is-open");
        } else {
            $panel.removeClass("is-open");
            $row.data("collapseTimer", setTimeout(function () {
                if (!$panel.hasClass("is-open")) {
                    $row.addClass("is-collapsed");
                }
            }, COLLAPSE_VISIBILITY_DELAY_MS));
        }
        setExpandAllState($toggle.closest(".submission-report"));
    }

    $("body").on("click", ".test-feedback-toggle", function () {
        setFeedbackOpen($(this), $(this).attr("aria-expanded") !== "true");
    });

    $("body").on("click", ".test-feedback-expand-all", function () {
        const $btn = $(this);
        const $report = $btn.closest(".submission-report");
        const expand = $btn.attr("data-expanded") !== "true";
        $report.find(".test-feedback-toggle").each(function () {
            const $toggle = $(this);
            const isOpen = $toggle.attr("aria-expanded") === "true";
            if (isOpen !== expand) {
                setFeedbackOpen($toggle, expand);
            }
        });
    });
});
