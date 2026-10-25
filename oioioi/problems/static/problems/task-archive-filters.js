$(document).ready(function() {
    const origintag = $("#filters").data("origintag");

    const search_tag = $(".search-tag");
    const checkbox_menu_toggle = $(".checkbox-menu-toggle");
    const checkbox_menu = $(".checkbox-menu");

    // Clicking a tag toggles whether its option is included in the filters.
    search_tag.on("click", function() {
        var value = $(this).find(".search-tag-text").text();
        var category = $(this).closest(".search-tags").prop("id");
        category = category.slice(0, category.length - "-search-tags".length);
        $("#" + category + "-filters")
            .find("input[type='checkbox']").filter("[value='" + value + "']")
            .click();
    });

    // Reimplement toggle to stop menu from closing on click
    checkbox_menu_toggle.on("click", function(e) {
        if ($(e.target).is(this)) {
            var target = $($(this).attr("data-bs-target"));
            if ($(this).hasClass("collapsed")) {
                checkbox_menu_toggle.addClass("collapsed");
                checkbox_menu.removeClass("show");
                $(this).removeClass("collapsed");
                target.addClass("show");
            } else {
                $(this).addClass("collapsed");
                target.removeClass("show");
            }
        }
    });

    checkbox_menu.on("change", "input[type='checkbox']", function() {
        $(this).closest("li").toggleClass("active", this.checked);

        var value = origintag + "_" + $(this).val();
        var label = $("input[value='" + value + "']").parent().parent();
        label.toggleClass("search-tag-inactive", !this.checked);
        label.find("input")
             .prop("disabled", !this.checked)
             .prop("readonly", this.checked);
    });

    // Disable bootstrap collapse transition as it is glitched with filter buttons
    $.fn.collapse.Constructor.TRANSITION_DURATION = 0;
});
