// https://github.com/twbs/bootstrap/issues/11037#issuecomment-274870381
$('.table-responsive').on('shown.bs.dropdown', function (e) {
    var t = $(this),
        m = $(e.target).find('.dropdown-menu'),
        tb = t.offset().top + t.height(),
        mb = m.offset().top + m.outerHeight(true),
        d = 20; // Space for shadow + scrollbar.
    if (t[0].scrollWidth > t.innerWidth()) {
        if (mb + d > tb) {
            t.css('padding-bottom', ((mb + d) - tb));
        }
    } else {
        t.css('overflow', 'visible');
    }
}).on('hidden.bs.dropdown', function () {
    $(this).css({'padding-bottom': '', 'overflow': ''});
});
