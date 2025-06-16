$(document).ready(function() {
    const menu = $('#menu-accordion');
    const subMenus = menu.find('.card-collapse');
    const openedClassName = 'show';

    // when a group is shown, save it as the active accordion group
    menu.on('shown.bs.collapse', function() {
        const activeId = menu.find('.' + openedClassName).attr('id');
        localStorage.setItem('activeMenuItem', activeId);
    });

    const saved = localStorage.getItem('activeMenuItem');
    if (saved !== null) {
        // remove default collapse settings
        subMenus.removeClass(openedClassName);

        const recentlyOpened = $('#' + saved);
        if (recentlyOpened.length) {
            recentlyOpened.addClass(openedClassName);
        } else {
            const lastMenuItem = menu.find('[id*="menu-"]').last();
            lastMenuItem.addClass(openedClassName);
        }
    }
});
