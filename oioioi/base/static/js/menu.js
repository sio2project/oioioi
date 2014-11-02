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

    // nonexp is a shorthand for nonexpandable
    var nonexps = menu_div.children().not('.nav-list');

    var last_visible_nonexp = function() {
        return nonexps.filter(':visible:last');
    };

    var first_hidden_nonexp = function() {
        return nonexps.filter(':hidden:first');
    };

    var can_hide = function() {
        return last_visible_nonexp().length || last_li().length;
    };

    var can_show = function() {
        return first_hidden_nonexp().length || submenu_first_li().length;
    };

    var hide_last = function() {
        var lvn = last_visible_nonexp();
        if (lvn.length == 1) {
            lvn.hide();
            return;
        }

        if (submenu_ul.is(':empty')) {
            submenu_divider.show();
            submenu.show();
        }

        last_li().prependTo(submenu_ul);
    };

    var show_last = function() {
        var sfl = submenu_first_li();
        if (sfl.length == 1) {
            sfl.insertBefore(submenu_divider);
            if (submenu_ul.is(':empty')) {
                submenu_divider.hide();
                submenu.hide();
            }
            return;
        }

        first_hidden_nonexp().show();
    };

    var last_visible_end = function() {
        var last_visible = menu_div.children(':visible:last');
        return last_visible.offset().top + last_visible.height();
    };

    var recalculate_menu = function() {
        if (menu_div.length === 0)
            return;

        var cut_y = footer.length ? footer.offset().top
                : menu_div.offset().top + $(window).height();

        while (can_show() && last_visible_end() < cut_y)
            show_last();

        while (can_hide() && last_visible_end() > cut_y)
            hide_last();
    };

    recalculate_menu();
    $(window).resize(recalculate_menu);
});
