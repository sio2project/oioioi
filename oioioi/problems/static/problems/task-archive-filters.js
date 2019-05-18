$(document).ready(function() {
    const origintag = $("#filters").data("origintag");

    const search_tag_remove = $(".search-tag-remove");
    const search_tag = $(".search-tag");
    const checkbox_menu_toggle = $(".checkbox-menu-toggle");
    const checkbox_menu = $(".checkbox-menu");

    search_tag_remove.on("click", function(e) {
        var value = $(this).parent().find(".search-tag-text").text();
        var checkbox = $("input[value='" + value + "']")
        checkbox.click();
        e.stopPropagation();
    });

    search_tag.on("click", function() {
        var value = $(this).find(".search-tag-text").text();
        var category = $(this).closest(".search-tags").prop("id");
        category = category.slice(0, category.length - "-search-tags".length);
        var checkboxes = $("#" + category + "-filters")
            .find("input:checked").filter("[value!='" + value + "']");
        checkboxes.click();
    });

    // Reimplement toggle to stop menu from closing on click
    checkbox_menu_toggle.on("click", function(e) {
        if ($(e.target).is(this)) {
            var target = $($(this).attr("data-target"));
            if ($(this).hasClass("collapsed")) {
                checkbox_menu_toggle.addClass("collapsed");
                checkbox_menu.removeClass("in");
                $(this).removeClass("collapsed");
                target.addClass("in");
            } else {
                $(this).addClass("collapsed");
                target.removeClass("in");
            }
        }
    });

    checkbox_menu.on("change", "input[type='checkbox']", function() {
        $(this).closest("li").toggleClass("active", this.checked);

        var category = $(this).closest("ul").prop('id');
        category = category.slice(0, category.length - "-filters".length);

        var value = origintag + "_" + $(this).val();
        var label = $("input[value='" + value + "']").parent().parent();
        if (this.checked) {
            label.find("input")
                 .prop("disabled", false)
                 .prop("readonly", true);
            label.show();
        } else {
            label.find("input")
                .prop("disabled", true)
                .prop("readonly", false);
            label.hide();
        }
    });

    // Disable bootstrap collapse transition as it is glitched with filter buttons
    $.fn.collapse.Constructor.TRANSITION_DURATION = 0;
});
