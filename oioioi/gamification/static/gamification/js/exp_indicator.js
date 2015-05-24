function setupExpIndicator(exp_info_url, widget_outer_radius) {
    var max_fps = 30;
    var interval = 1000 / max_fps;

    var animation_seq_num = 0;

    function smoothAddExp(widget, initial_exp, initial_lvl, exp_to_add) {
        var exp_added = 0;

        var current_exp = initial_exp;
        var current_lvl = initial_lvl;

        var current_seq_num = animation_seq_num;

        var then = window.performance.now();

        function tick(timestamp) {
            if (current_seq_num != animation_seq_num)
                return;

            if (exp_added >= exp_to_add) {
                var total = initial_exp + exp_to_add;
                current_exp = total % 100;
                current_lvl = Math.floor(total / 100) + initial_lvl;
                setExp(widget, current_exp, current_lvl);
                return;
            }

            window.requestAnimationFrame(tick);

            var dt = timestamp - then;
            if (dt < interval)
                return;

            then = timestamp - (dt % interval);

            var x = exp_added / exp_to_add;
            var y = (-Math.pow(2 * x - 1, 4) + 1) * 3 + 0.1;
            y = 3 * y * exp_to_add / 100;

            exp_added += y;
            current_exp += y;
            if (current_exp >= 100) {
                current_exp %= 100;
                current_lvl += 1;
            }

            setExp(widget, current_exp, current_lvl);
        }

        tick(then);
    }

    function setExp(widget, exp, lvl) {
        exp = exp / 100 * 2 * Math.PI;

        var seg = widget.children('path').get(0).pathSegList.getItem(2);
        seg.x = widget_outer_radius * Math.sin(exp);
        seg.y = widget_outer_radius * (1 - Math.cos(exp));
        seg.largeArcFlag = exp > Math.PI;

        widget.children('text').text(lvl);
    }

    $(function() {
        $.ajax({
            url: exp_info_url,
            type: 'GET',
            dataType: 'json'
        }).done(function(data) {
            var indicator = $('#submit .exp-indicator');
            var after = indicator.children('.after');

            $('#submit input').hover(function() {
                indicator.one('webkitAnimationEnd oanimationend msAnimationEnd'
                        + ' animationend', function() {
                    smoothAddExp(after.children('svg'), data.current_exp,
                            data.current_lvl, data.exp_to_add);
                });

                indicator.removeClass('animate');
                indicator.hide().show(0); // force redraw
                indicator.addClass('animate');
                indicator.show();
            }, function() {
                indicator.hide();
                ++animation_seq_num;
                setExp(after.children('svg'), data.current_exp,
                        data.current_lvl);
            });
        });
    });
}

