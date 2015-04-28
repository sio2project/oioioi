$(function() {
    var animationDuration = 500;
    $('.portal-menu-siblings').each(function() {
        var self = $(this);
        var parent = $(this).parent();
        var a = parent.children('a');
        var chevron = parent.find('.icon-chevron-down');
        var inTimeout, outTimeout;
        var orientation = 0;
        parent.hover(function() {
            a.addClass('hover');

            clearTimeout(outTimeout);
            inTimeout = setTimeout(function() {
                self.stop(true).css('display', 'block').animate({
                    left: '100%',
                    opacity: 1
                }, animationDuration);

                chevron.stop(true, true);
                $({deg: orientation}).animate({deg: -90}, {
                    step: function(now) {
                        chevron.css({transform: 'rotate(' + now + 'deg)'});
                        orientation = now;
                    },
                    duration: animationDuration
                });
            }, 400);
        }, function() {
            a.removeClass('hover');
            clearTimeout(inTimeout);

            outTimeout = setTimeout(function() {
                self.stop(true).animate({
                    left: '0',
                    opacity: 0
                }, animationDuration);
                outTimeout = setTimeout(function() {
                    self.css('display', 'none');
                }, animationDuration);

                chevron.stop(true, true);
                $({deg: orientation}).animate({deg: 0}, {
                    step: function(now) {
                        chevron.css({transform: 'rotate(' + now + 'deg)'});
                        orientation = now;
                    },
                    duration: animationDuration
                });
            }, 400);
        });

        var url = a.attr('href');
        var height = parent.height() + 1;
        var top = -3;
        $(this).children('li').each(function() {
            if($(this).children('a').attr('href') == url)
                return false;
            top -= height;
        });
        $(this).css('top', top + 'px');
    });
});
