$(function() {
    var animationDuration = 500;
    var delayDuration = 400;

    $('.portal-menu-siblings').each(function() {
        var self = $(this);
        var parent = $(this).parent();
        var a = parent.children('a');
        var chevron = parent.find('.icon-chevron-down');
        var inTimeout, outTimeout;
        var orientation = 0;

        function rotateChevron(deg) {
            chevron.stop(true, true);
            $({deg: orientation}).animate({deg: deg}, {
                step: function(now) {
                    chevron.css({transform: 'rotate(' + now + 'deg)'});
                    orientation = now;
                },
                duration: animationDuration
            });
        }

        function showMenuSiblings() {
            self.stop(true).css('display', 'block').animate({
                left: '100%',
                opacity: 1
            }, animationDuration);
        }

        function hideMenuSiblings() {
            self.stop(true).animate({
                left: '0',
                opacity: 0
            }, animationDuration, 'swing', function() {
                self.css('display', 'none');
            });
        }

        parent.hover(function() {
            a.addClass('hover');

            // stop any hiding in progress
            clearTimeout(outTimeout);

            // it feels more natural with a slight delay
            inTimeout = setTimeout(function() {
                showMenuSiblings();
                rotateChevron(-90);
            }, delayDuration);
        }, function() {
            a.removeClass('hover');

            // stop any showing in progress
            clearTimeout(inTimeout);

            outTimeout = setTimeout(function() {
                hideMenuSiblings();
                rotateChevron(0);
            }, delayDuration);
        });
    });
});
