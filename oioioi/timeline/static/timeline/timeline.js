$(document).ready(function() {
    // round date to full hours
    function round(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(),
                date.getHours(), 0, 0, 0);
    }

    function round_to_seconds(date) {
        return new Date(Math.round(date.getTime() / 1000) * 1000);
    }

    var GROUP_ICON_CLASS = 'group-icon';
    var GROUP_ICON_HTML = '<i class="' + GROUP_ICON_CLASS +
                    ' icon-list-alt icon-white"></i>';
    var DATE_FORMAT = 'yyyy-MM-dd hh:mm';
    // max distance (in px) between 2 datepickers that will be connected
    var MAX_DISTANCE = 15;
    // max value of the css top property of a datebox
    // it's equal to the timeline height - datebox height
    var MAX_Y = 670;
    // the fraction of the timeline height that is taken by the gaps
    var DATE_RANGE_GAP = 1/7;
    var ONE_DAY = 24 * 60 * 60 * 1000;

    var min_date;
    var max_date;
    // for every datebox id keep ids of the elements hidden in its group
    var datebox_groups = {};

    // empty group contains just the parent element
    function clear_group(parent_id) {
        datebox_groups[parent_id] = {};
        datebox_groups[parent_id][parent_id] = true;
    }

    function position_to_date(pos) {
        return round(new Date((max_date.getTime() - min_date.getTime()) * pos /
                MAX_Y + min_date.getTime()));
    }

    function date_to_position(date) {
        return MAX_Y * (date.getTime() - min_date.getTime()) /
                (max_date.getTime() - min_date.getTime());
    }

    function reset_z_index() {
        $('.datebox').each(function() {
            $(this).css('z-index', 'auto');
        });
    }

    function move_to_foreground($datebox) {
        reset_z_index();
        $datebox.css('z-index', '1000');
    }

    function get_order($datebox) {
        return $datebox.attr('id').split('_')[1];
    }

    function get_group_parent_id(datebox_id) {
        var parent_id = datebox_id;
        $.each(datebox_groups, function(key, val) {
            if(key != datebox_id && val[datebox_id]) {
                parent_id = key;
                return false;
            }
        });
        return parent_id;
    }

    // return id of the child from the group that is not the parent and has the
    // lowest order or the parent id if it is the only element in the group
    function get_first_child_id(parent_id) {
        var child_id = Object.keys(datebox_groups[parent_id]).filter(
                function(key) {
            return key != parent_id;
        }).sort(function(a, b) {
           return get_order($('#' + a)) < get_order($('#' + b));
        })[0];

        if(child_id) {
            return child_id;
        } else {
            return parent_id;
        }
    }

    // generates content for the group icon tooltip
    function generate_tooltip_content($group_parent) {
        var tooltip_html = '<ul class="tooltip-list">';
        $.each(datebox_groups[$group_parent.attr('id')], function(key, val) {
            var event_title = $('#' + key).children('.date-title').text();
            tooltip_html += '<li>' + event_title + '</li>';
        });
        tooltip_html += '</ul>';
        return tooltip_html;
    }

    function generate_popover_content($group_parent) {
        var popover_content = '<div class="popover-body">';
        $.each(datebox_groups[$group_parent.attr('id')], function(key, val) {
            var event_title = $('#' + key).children('.date-title').text();
            popover_content +=
                '<div id="_' + key +'" ' +
                    'class="popover-datebox btn-primary inline pull-left">' +
                    '<span class="date-title inline pull-left">' +
                        event_title +
                    '</span>' +
                    '<i class="group-delete-btn icon-remove icon-white"></i>' +
                '</div>';
        });
        popover_content += '</div>';
        return popover_content;
    }

    function disable_group_icon($group_parent) {
        $group_parent.children('.' + GROUP_ICON_CLASS).tooltip('hide').
                popover('hide');
        $group_parent.off('mouseenter mouseleave click',
                '.' + GROUP_ICON_CLASS);
    }

    function enable_group_icon($group_parent) {
        // makes sure not to attach the handlers twice
        disable_group_icon($group_parent);
        $group_parent.on({
            mouseenter: function() {
                $(this).tooltip('show');
            },
            mouseleave: function() {
                $(this).tooltip('hide');
            },
            click: function() {
                $(this).tooltip('hide').popover('toggle');
            }
        }, '.' + GROUP_ICON_CLASS);
    }

    function add_group_icon(group_parent) {
        var $group_parent = $(group_parent);
        $group_parent.append(GROUP_ICON_HTML);
        // init group tooltip
        $group_parent.children('.' + GROUP_ICON_CLASS).tooltip({
            animation: false,
            html: true,
            placement: 'right',
            trigger: 'manual',
            title: generate_tooltip_content($group_parent),
            container: 'body'
        }).popover({
            animation: false,
            html: true,
            placement: 'right',
            trigger: 'manual',
            content: generate_popover_content($group_parent),
            container: '#timeline-wrapper'
        });
        enable_group_icon($group_parent);
    }

    function remove_group_icon($group_parent) {
        $group_parent.children('.' + GROUP_ICON_CLASS).tooltip('destroy').
                popover('destroy').remove();
    }

    function set_popover_state($group_parent, state) {
        var group_icon = $group_parent.children('.' + GROUP_ICON_CLASS);
        if(group_icon) {
            group_icon.popover(state);
        }
    }

    function get_date($datebox) {
        return $datebox.children('.date').data('datetimepicker').getDate();
    }

    function set_date($datebox, new_date) {
        $datebox.children('.date').data('datetimepicker').setDate(new_date);
    }

    function set_group_date($datebox, new_date) {
        var group_parent_id = get_group_parent_id($datebox.attr('id'));
        $.each(datebox_groups[group_parent_id], function(key, val) {
            set_date($('#' + key), new_date);
        });
    }


    function get_dates_range() {
        var dates = $('.datebox').map(function() {
            return get_date($(this));
        });

        return {
            min_date: new Date(Math.min.apply(null, dates)),
            max_date: new Date(Math.max.apply(null, dates))
        };
    }

    function update_date_range() {
        var range = get_dates_range();
        var date_delta = range['max_date'].getTime() -
                range['min_date'].getTime();
        // calculate the gap in ms so that the gaps in the begining an in
        // the end of the timeline take in total DATE_RANGE_GAP fraction
        // of total height of the timeline, but not less then ONE_DAY
        var date_range_gap_in_ms = Math.max(date_delta * DATE_RANGE_GAP /
                (2 - 2 * DATE_RANGE_GAP), ONE_DAY);
        min_date = new Date(range['min_date'].getTime() -
                date_range_gap_in_ms);
        max_date = new Date(range['max_date'].getTime() +
                date_range_gap_in_ms);
    }

    function adjust_datebox_positions() {
        $('.datebox').each(function() {
            $(this).css('top', date_to_position(get_date($(this))));
        });
    }

    function change_date_handler() {
        update_date_range();
        adjust_datebox_positions();
    }

    function get_closest_datebox($datebox) {
        var datebox_y = $datebox.position().top;
        return $('.datebox').filter(function() {
            var $this = $(this);
            return $datebox.attr('id') != $this.attr('id') && $this.is(':visible');
        }).sort(function(a, b) {
            // we want only the closest datepicker
            var a_y = $(a).position().top;
            var b_y = $(b).position().top;
            return Math.abs(datebox_y - a_y) < Math.abs(datebox_y - b_y) ? -1 : 1;
        }).get(0);
    }

    function connect_groups($group_item, $datebox_to_connect) {
        var $group_parent = $('#' + get_group_parent_id($group_item.
                attr('id')));
        var $parent_to_connect = $('#' + get_group_parent_id(
                $datebox_to_connect.attr('id')));
        if(get_order($group_parent) > get_order($parent_to_connect)) {
            var tmp = $group_parent;
            $group_parent = $parent_to_connect;
            $parent_to_connect = tmp;
        }

        var group_parent_id = $group_parent.attr('id');
        var parent_to_connect_id = $parent_to_connect.attr('id');

        // remove group icons
        remove_group_icon($parent_to_connect);
        remove_group_icon($group_parent);
        // hide the datepickerbox and its tooltip
        $parent_to_connect.hide().tooltip('hide');
        // add the datepicker to the group
        $.each(datebox_groups[parent_to_connect_id],
            function(key, val) {
                datebox_groups[group_parent_id][key] = true;
        });
        clear_group(parent_to_connect_id);
        add_group_icon($group_parent);
        // update dates and positions
        set_group_date($parent_to_connect, get_date($group_parent));
        change_date_handler();
    }

    function is_in_connection_distance($datebox1, $datebox2) {
        return $datebox1.length && $datebox2.length && Math.abs(
                $datebox1.position().top - $datebox2.position().top) <
                MAX_DISTANCE;
    }

    window.init_timeline = function(lang_code) {
        // hack fixing dragging performance
        // source: http://blog.toggl.com/2013/02/increasing-perceived-performance-with-_throttle/
        var drag_active = false;

        var original_mouseMove = jQuery.ui.mouse.prototype._mouseMove;
        jQuery.ui.mouse.prototype._mouseMove = function() {
          if(drag_active) {
            original_mouseMove.apply(this, arguments);
          }
        };
        var original_mouseDown = jQuery.ui.mouse.prototype._mouseDown;
        jQuery.ui.mouse.prototype._mouseDown = function() {
          drag_active = true;
          original_mouseDown.apply(this, arguments);
        };
        var original_mouseUp = jQuery.ui.mouse.prototype._mouseUp;
        jQuery.ui.mouse.prototype._mouseUp = function() {
          original_mouseUp.apply(this, arguments);
          drag_active = false;
        };
        jQuery.ui.mouse.prototype._mouseMove =
                _.throttle(jQuery.ui.mouse.prototype._mouseMove, 40);

        // init connection tooltip
        $('.datebox').tooltip({
            placement: 'right',
            trigger: 'manual',
            container: 'body',
            title: gettext("Drop to connect"),
            animation: false
        });

        $('.date').datetimepicker({
            format: DATE_FORMAT,
            language: lang_code,
            pickSeconds: false
        });

        $('.datebox').draggable({
            containment: $('#timeline'),
            start: function() {
                var $dragged_datebox = $(this);
                move_to_foreground($dragged_datebox);
                disable_group_icon($dragged_datebox);
            },
            drag: function() {
                var $dragged_datebox = $(this);
                var dragged_datebox_y = $dragged_datebox.position().top;
                var new_date = position_to_date(dragged_datebox_y);
                set_date($dragged_datebox, new_date);
                var $closest_datebox = $(get_closest_datebox($dragged_datebox));
                if(is_in_connection_distance($closest_datebox,
                        $dragged_datebox)) {
                    $dragged_datebox.tooltip('show');
                } else {
                    $dragged_datebox.tooltip('hide');
                }
            },
            stop: function() {
                var $dragged_datebox = $(this);
                $dragged_datebox.tooltip('hide');
                set_group_date($dragged_datebox, get_date($dragged_datebox));
                var $closest_datebox = $(get_closest_datebox($dragged_datebox));
                if(is_in_connection_distance($closest_datebox,
                        $dragged_datebox)) {
                    connect_groups($closest_datebox, $dragged_datebox);
                } else {
                    enable_group_icon($dragged_datebox);
                }
                change_date_handler();
            }
        });

        $('.datebox').click(function() {
            move_to_foreground($(this));
        });

        $(document).on('click', '.group-delete-btn', function(e) {
            var event_trigger = e.currentTarget;
            var to_delete_id = $(event_trigger).parent().attr('id').
                    substring(1);
            var parent_id = get_group_parent_id(to_delete_id);
            var $to_delete = $('#' + to_delete_id);
            var $parent = $('#' + parent_id);

            var children_in_group = 0;
            $.each(datebox_groups[parent_id], function() {
                children_in_group++;
            });

            if(children_in_group > 1) {
                remove_group_icon($parent);
                if(to_delete_id == parent_id) {
                    // parent of a nonempty group is about to be deleted
                    // make it a child of the group
                    var new_parent_id = get_first_child_id(parent_id);
                    var $new_parent = $('#' + new_parent_id);
                    datebox_groups[new_parent_id] = datebox_groups[parent_id];
                    clear_group(parent_id);
                    $parent.hide();
                    $new_parent.show();
                    parent_id = new_parent_id;
                    $parent = $new_parent;
                }
                delete datebox_groups[parent_id][to_delete_id];
                if(children_in_group > 2) {
                    add_group_icon($parent);
                }
                $to_delete.show();
                set_popover_state($parent, 'show');
            }
        });

        // adjust y position and date range on date change
        $('.date').on('changeDate', function(e) {
            var $datebox = $('#' + get_group_parent_id($(e.currentTarget).
                                                        parent().attr('id')));
            var new_date = e.date;
            set_group_date($datebox, new_date);
            change_date_handler();
        });
        // init datebox_groups dictionary
        $('.datebox').each(function() {
            clear_group($(this).attr('id'));
        });
        // set the inital dates range and dateboxes positions
        // based on the inital datepickers values
        change_date_handler();
        var datebox_array = $('.datebox').sort(function(a,b) {
            return get_date($(a)) < get_date($(b));
        }).get();
        for(var i = 0; i < datebox_array.length - 1; i++) {
            if(round_to_seconds(get_date($(datebox_array[i]))) ==
                    round_to_seconds(get_date($(datebox_array[i+1])))) {
                connect_groups($(datebox_array[i]), $(datebox_array[i+1]));
            }
        }
    };
});
