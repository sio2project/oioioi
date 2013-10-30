$(window).load(function() {
    var menu_div = $('#menu_div');
    var menu_ul = menu_div.find('.nav-list');
    var last_li = function() {
        return menu_ul.children('li:nth-last-of-type(3)');
    };
    var submenu = menu_ul.find('.nav-dropdown-submenu');
    var submenu_ul = submenu.children('ul');
    var submenu_first_li = function() {
        return submenu_ul.children('li:first');
    };
    var submenu_divider = $('#nav-dropdown-divider');
    var footer = $('.body-with-menu footer');


    var hide_first = function() {
        if (submenu_ul.is(':empty')) {
            submenu_divider.show();
            submenu.show();
        }

        last_li().prependTo(submenu_ul);
    };

    var show_first = function() {
        submenu_first_li().insertBefore(submenu_divider);
        if (submenu_ul.is(':empty')) {
            submenu_divider.hide();
            submenu.hide();
        }
    };

    var recalculate_menu = function() {
        if (menu_div.length === 0)
            return;

        var cut_y = footer.length ? footer.offset().top
                : menu_div.offset().top + $(window).height();

        while (submenu_first_li().length == 1 &&
                menu_ul.offset().top + menu_ul.height() < cut_y) {
            show_first();
        }

        while (last_li().length == 1 &&
                menu_ul.offset().top + menu_ul.height() > cut_y) {
            hide_first();
        }
    };

    recalculate_menu();
    $(window).resize(recalculate_menu);
});
