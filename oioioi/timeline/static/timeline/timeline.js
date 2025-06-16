import { initDateTimePicker } from '../../../base/static/js/datetimepicker';

$(function() {
    var $timeline_form = $('#timeline-form');
    var $timeline = $timeline_form.find('.oioioi-timeline');

    // the fraction of the timeline height that is taken by the gaps
    var DATE_RANGE_GAP = 1/7;
    var ONE_DAY = 24 * 60 * 60 * 1000;

    // Minimal distance between the active datebox and the window's border
    var TOP_MARGIN = 100;
    var BOTTOM_MARGIN = 100;
    // Scrolling animation time
    var SCROLLING_TIME = 500;

    var ROUND_BAR_CLASS = 'oioioi-timeline__round-bar';
    var ROUND_BAR_HTML = '<div class="' + ROUND_BAR_CLASS + '"></div>';
    var ROUND_GROUP_WIDTH = 35;
    var ROUND_BAR_WIDTH = 30;

    // we don't want vertical connector parts to overlap, we draw every
    // subsequent connector a little bit more to the left if that should
    // be the case.
    var CONNECTOR_DISPLACEMENT = 10;
    // we use this to correct event-margin position offset
    var CONNECTOR_EVENT_MARGIN = 1;
    var CONNECTOR_HTML = $.map(['event', 'left', 'mid', 'right'],
        function(type) {
            return '<div class="oioioi-timeline__connector ' +
                    'oioioi-timeline__connector--' + type + '"></div>';
        }
    );

    var POPOVER_CONTENT = gettext('Change date in a datebox by clicking \
the corresponding <span class="fa-solid fa-calendar"></span> button. \
You can also use the keyboard: \
<br> \
<ul> \
<li><strong>TAB</strong> - go to the next datebox</li> \
<li><strong>ENTER</strong> - confirm date</li> \
<li><strong>ESC, CTRL+Z</strong> - reset date</li> \
</ul> \
<hr> \
You can filter events by clicking the vertical bar representing a round. \
<hr> \
If you want to split a date group, click the corresponding \
<span class="fa-solid fa-arrows-up-down"></span> button.'
    );

    var SEPARATOR_HTML = '<div class="oioioi-timeline__separator"></div>';

    var NOW_BAR_HTML = '<div class="oioioi-timeline__now-bar"><small>' +
        gettext("now") + '</small></div>';


    var DATEBOX_HEIGHT = parseInt($('.form-control').css('height'), 10) + 2;
    // a horizontal gap between round bars and datepickers
    var DATEBOX_GAP = 40;
    // a vertical gap used to separate datepickers with no date specified
    var NO_DATE_GAP = 60;
    // space between rounds and their labels
    var LABEL_GAP = 30;
    // width of the date input field
    var INPUT_WIDTH = 265;

    // created with the use of http://www.palettefx.com
    var PALETTE = [
        [238, 119, 68],
        [85, 153, 187],
        [102, 119, 136],
        [238, 204, 85],
        [136, 187, 221],
        [221, 170, 17],
        [187, 85, 34],
        [17, 136, 170],
        [17, 68, 102],
        [153, 136, 85],
    ];

    var GREEN_OFFSET = 10;
    var GRADIENT_STRINGS = [
        '-webkit-linear-gradient(bottom, ',
        '-o-linear-gradient(top, ',
        '-moz-linear-gradient(top, ',
        'linear-gradient(to bottom, ',
    ];

    var DIM_CLASS = 'oioioi-timeline__round-group--dim';
    var UNDIM_CLASS = 'oioioi-timeline__round-group--undim';

    var min_date;
    var max_date;
    // length of the time axis
    var timeline_height = 700;
    // for every datebox id keep ids of the elements hidden in its group
    var datebox_groups = {};

    function rgb_to_string(rgb) {
        return 'rgb(' + rgb[0] + ', ' + rgb[1] + ', ' + rgb[2] + ')';
    }

    function get_gradient(id) {
        var col1 = PALETTE[id];
        var col2 = [
            col1[0],
            Math.min(255, col1[1] + GREEN_OFFSET),
            col1[2]
        ];
        return rgb_to_string(col1) + ', ' + rgb_to_string(col2);
    }

    function set_gradient($datebox, color_id) {
        var color_string = get_gradient(color_id) + ')';
        $.each(GRADIENT_STRINGS, function() {
            $datebox.css('background-image', this + color_string);
        });
    }

    function get_date($datebox) {
        return $datebox.children('.date').data('TempusDominus').dates.lastPicked ?? null;
    }

    function set_date($datebox, new_date) {
        $datebox.children('.date').data('TempusDominus').dates.setValue(new_date, 0)
    }

    function set_width($datebox) {
        let width = $datebox.find('.oioioi-timeline__date-title').width();
        var new_width = Math.max(parseInt($datebox.css('min-width'), 10),
            INPUT_WIDTH + width);
        $datebox.css('width', new_width);
    }

    function get_dates_range() {
        var dates = $timeline.find('.oioioi-timeline__datebox')
            .map(function() {
                return get_date($(this));
            });

        return {
            min_date: new Date(Math.min.apply(null, dates)),
            max_date: new Date(Math.max.apply(null, dates))
        }; 
    }

    function update_date_range() {
        var range = get_dates_range();
        var date_delta = range.max_date.getTime() -
            range.min_date.getTime();
        // calculate the gap in ms so that the gaps in the begining an in
        // the end of the timeline take in total DATE_RANGE_GAP fraction
        // of total height of the timeline, but not less then ONE_DAY
        var date_range_gap_in_ms = Math.max(date_delta * DATE_RANGE_GAP /
            (2 - 2 * DATE_RANGE_GAP), ONE_DAY);
        min_date = new Date(range.min_date.getTime() -
            date_range_gap_in_ms);
        max_date = new Date(range.max_date.getTime() +
            date_range_gap_in_ms);
    }

    function date_to_position(date) {
        return timeline_height * (date.getTime() - min_date.getTime()) /
            (max_date.getTime() - min_date.getTime());
    }

    function create_round_bars() {
        var left = 0;
        var max_width = 0;
        $timeline.children('.oioioi-timeline__round-group')
            .each(function() {
                var $this = $(this);
                $this.css('left', left);
                left += ROUND_GROUP_WIDTH;
                var $round_label = $this.find(
                    '.oioioi-timeline__round-label');
                if ($round_label.length > 0) {
                    $this.append(ROUND_BAR_HTML);
                    max_width = Math.max(max_width,
                        $round_label.find('strong').width());
                }
            });
        max_width = max_width / Math.sqrt(2) + LABEL_GAP;
        var $wrapper = $timeline_form.find('.oioioi-timeline');
        var current_margin = parseInt($wrapper.css('margin-top'));
        if (max_width > current_margin) {
            $wrapper.css('margin-top', max_width);
        }
    }

    function assign_colors() {
        var color_id = 0;
        $timeline.find('.oioioi-timeline__round-group').each(function() {
            var color_string = rgb_to_string(PALETTE[color_id]);
            $(this).find('.oioioi-timeline__round-bar')
                .css('background', color_string);
            $(this).find('.oioioi-timeline__round-label')
                .css('color', color_string);
            set_gradient($(this)
                .find('.oioioi-timeline__datebox'), color_id);
            color_id = (color_id + 1) % PALETTE.length;
        });
    }

    function adjust_bar_positions() {
        $timeline
            .children('.oioioi-timeline__round-group')
            .each(function() {
                var $this = $(this);
                var roundBarLength = $this.children(
                    '.oioioi-timeline__round-bar').length;
                if (roundBarLength > 0) {
                    var start_date = get_date($this.children(
                        ".oioioi-timeline__datebox" +
                            "[data-timeline-type=start]"));
                    var end_date = get_date($this.children(
                        ".oioioi-timeline__datebox" +
                            "[data-timeline-type=end]"));
                    var start_y, end_y;
                    if (start_date !== null) {
                        start_y = date_to_position(start_date);
                    } else {
                        start_y = 0;
                    }
                    if (end_date !== null) {
                        end_y = date_to_position(end_date);
                    } else {
                        end_y = timeline_height;
                    }
                    $this.children('.oioioi-timeline__round-bar').css(
                        {top: start_y, height: end_y - start_y});
                }
            });
    }

    function compare_dateboxes($a, $b) {
        var r1 = $a.attr('data-timeline-round-num');
        var r2 = $b.attr('data-timeline-round-num');
        if (r1 !== r2) return r1 - r2;
        var o1 = $a.attr('data-timeline-order');
        var o2 = $b.attr('data-timeline-order');
        if (o1 !== o2) return o1 - o2;
        return $a.attr('data-timeline-entry-num') -
            $b.attr('data-timeline-entry-num');
    }

    function compare_dates(a, b) {
        var $a = $(a);
        var $b = $(b);
        var d1 = get_date($a);
        var d2 = get_date($b);
        if (d1 === null && d2 === null) return compare_dateboxes($a, $b);
        if (d1 === null) return 1;
        if (d2 === null) return -1;
        var t1 = d1.getTime();
        var t2 = d2.getTime();
        if (t1 !== t2) return t1 - t2;
        return compare_dateboxes($a, $b);
    }

    function adjust_connectors($datebox, datebox_left, y_offset,
            overlapping) {
        var $event = $datebox.children(
            '.oioioi-timeline__connector--event');
        var $left = $datebox.children(
            '.oioioi-timeline__connector--left');
        var $mid = $datebox.children(
            '.oioioi-timeline__connector--mid');
        var $right = $datebox.children(
            '.oioioi-timeline__connector--right');
        var $group = $datebox.parent();
        var len_r = $group.position().left +
            overlapping * CONNECTOR_DISPLACEMENT;
        var len_l = datebox_left - len_r;
        $left.css({left: -datebox_left, width: len_l, top: -y_offset});
        $mid.css({left: -len_r, height: y_offset, top: -y_offset});
        $right.css({left: -len_r, width: len_r});
        var has_event = $(datebox_groups[$datebox.attr('id')])
            .filter(
                function() {
                    return $(this).attr('data-timeline-type') === 'None';
                }
            ).length > 0;
        if (has_event) {
            $event.css({left: -datebox_left,
                    top: -(y_offset + CONNECTOR_EVENT_MARGIN)});
        } else {
            $event.hide();
        }
    }

    function simulate_overlapping(datebox_array) {
        var current_top = 0;
        var overlapping = 0;
        var max_overlapping = 0;
        $.each(datebox_array, function() {
            var $this = $(this);
            if (!$this.is(':visible')) {
                return true;
            }
            var my_date = get_date($this);
            if (my_date === null) {
                return true;
            }
            var target_position = date_to_position(my_date);
            var my_top;
            if (current_top > target_position) {
                my_top = current_top;
                overlapping++;
                max_overlapping = Math.max(max_overlapping, overlapping);
            } else {
                my_top = target_position;
                overlapping = 0;
            }
            current_top = my_top + DATEBOX_HEIGHT;
        });
        return max_overlapping;
    }

    function adjust_datebox_positions() {
        var datebox_array = $timeline.find('.oioioi-timeline__datebox')
            .get().sort(compare_dates);
        var rounds_num =
            $timeline.children('.oioioi-timeline__round-group').length;
        var current_top = 0;
        var max_nonempty_top = 0;
        var overlapping = 0;
        var empty_boxes = 0;
        var max_overlapping = simulate_overlapping(datebox_array);
        var default_left = rounds_num * ROUND_GROUP_WIDTH + DATEBOX_GAP;
        var datebox_left = default_left +
            max_overlapping * CONNECTOR_DISPLACEMENT;
        var tabindex = 1;
        $.each(datebox_array, function() {
            var $this = $(this);
            if (!$this.is(':visible')) {
                return true;
            }
            var roundGroupLeft = $this.parents(
                '.oioioi-timeline__round-group').position().left;
            var my_date = get_date($this);
            var target_position;
            var my_top;
            if (my_date !== null) {
                target_position = date_to_position(my_date);
            } else {
                if (max_nonempty_top === 0) {
                    max_nonempty_top = current_top;
                }
                target_position = timeline_height + NO_DATE_GAP;
            }
            if (current_top > target_position) {
                my_top = current_top;
                overlapping++;
            } else {
                my_top = target_position;
                overlapping = 0;
            }
            $this.css({left: datebox_left, top: my_top});
            set_width($this);
            if (my_date !== null) {
                $this.children('.oioioi-timeline__connector').show();
                adjust_connectors($this, datebox_left,
                        my_top - target_position, overlapping);
            } else {
                $this.children('.oioioi-timeline__connector').hide();
                empty_boxes++;
            }
            $this.find('input').attr('tabindex', tabindex);
            tabindex++;
            current_top = my_top + DATEBOX_HEIGHT;
        });
        // we have to stretch timeline due to empty dateboxes.
        $timeline.css('height', DATEBOX_HEIGHT +
            Math.max(current_top, timeline_height));
        $timeline.find('.oioioi-timeline__separator').css('top',
            Math.max(max_nonempty_top, timeline_height) + NO_DATE_GAP / 2);
        $timeline.find('.oioioi-timeline__now-bar')
            .css('width', datebox_left);
    }

    function adjust_now_bar() {
        var $now_bar = $timeline.find('.oioioi-timeline__now-bar');
        var now_position = date_to_position(new Date());
        if (now_position >= 0 && now_position <= timeline_height) {
            $now_bar.show();
            $now_bar.css('top', now_position - parseInt(
                    $now_bar.css('height')));
        } else {
            $now_bar.hide();
        }
    }

    function change_date_handler() {
        update_date_range();
        adjust_bar_positions();
        adjust_datebox_positions();
        adjust_now_bar();
    }

    function set_group_date($datebox, new_date) {
        $(datebox_groups[$datebox.attr('id')]).each(function() {
            var $this = $(this);
            set_date($this, new_date);
            $this.find('input').addClass(
                'oioioi-timeline__date-input--date-changed');
        });
    }

    function process_groups(datebox_array) {
        $.each(datebox_array, function() {
            var $first_datebox = $(this);
            var in_group = $(datebox_groups[$first_datebox.attr('id')]);

            if (in_group.length > 1) {
                in_group.sort(compare_dateboxes);
                var $main_datebox = in_group[0];
                var secondary_titles = [];

                $.each(in_group, function() {
                    var $this = $(this);
                    var title = $this.find('.oioioi-timeline__date-title')
                            .text();
                    if ($this.attr('id') === $main_datebox.attr('id')) {
                        $this.addClass('oioioi-timeline__datebox-group');
                    } else {
                        secondary_titles.push(title);
                        $this.hide();
                    }
                });
                var all_titles = ' | ' + secondary_titles.reduce(
                    function(prev, curr) {
                            return prev + ', ' + curr;
                    }
                );
                $main_datebox.find('.oioioi-timeline__date-title small')
                    .text(all_titles);
                // swap datebox_groups between $first_datebox and
                // $main_datebox
                datebox_groups[$first_datebox.attr('id')] =
                    [$first_datebox];
                datebox_groups[$main_datebox.attr('id')] = in_group;
            }
        });
    }

    function create_groups() {
        $timeline.find('.oioioi-timeline__round-group').each(function() {
            var datebox_array = $(this).find('.oioioi-timeline__datebox')
                .get().sort(compare_dates);
            var prev_date = null;
            var prev_datebox_id = null;
            $.each(datebox_array, function() {
                var $this = $(this);
                var curr_date = get_date($this);
                datebox_groups[$this.attr('id')] = [$this];
                if (curr_date === null) {
                    return true;
                }
                if (prev_date !== null && prev_date.getTime() ===
                        curr_date.getTime()) {
                    datebox_groups[prev_datebox_id].push($this);
                } else {
                    prev_datebox_id = $this.attr('id');
                    prev_date = curr_date;
                }
            });
            process_groups(datebox_array);
        });
    }

    function create_now_bar() {
        $timeline.append(NOW_BAR_HTML);
    }

    function create_connectors() {
        $timeline.find('.oioioi-timeline__datebox').each(function() {
            $(this).append(CONNECTOR_HTML);
        });
    }

    function create_hint() {
        $timeline_form.find('.btn-hint').popover({
            trigger: 'focus',
            html: true,
            placement: 'bottom',
            content: POPOVER_CONTENT
        });
    }

    function create_lines() {
        $timeline.append(SEPARATOR_HTML);
    }

    function split_group($datebox) {
        $datebox.removeClass('oioioi-timeline__datebox-group');
        var my_id = $datebox.attr('id');
        $datebox.find('.oioioi-timeline__date-title small').text('');
        $.each(datebox_groups[my_id], function() {
            $(this).show();
        });
        datebox_groups[my_id] = [$datebox];
    }

    function change_group_state($group, type) {
        $group.find('.date').each(function() {
            var data = $(this).data('TempusDominus');
            if (type) {
                data.disable();
            } else {
                data.enable();
            }
        });
    }

    function change_dim_state(type) {
        $timeline.find('.oioioi-timeline__round-group').each(function() {
            var $this = $(this);
            $this.removeClass(UNDIM_CLASS);
            if (type) {
                $this.addClass(DIM_CLASS);
            } else {
                $this.removeClass(DIM_CLASS);
            }
            change_group_state($this, type);
        });
    }

    function custom_undo(e) {
        // Ctrl+z or ESC
        if (
            (e.key === 'z' && (e.ctrlKey || e.metaKey)) ||
            e.key === 'Escape'
        ) {
            e.preventDefault();
            var $datebox = $(e.target)
                .parents('.oioioi-timeline__datebox');
            if ($datebox.length === 1 &&
                    $timeline.has($datebox).length === 1) {
                set_date($datebox, get_date($datebox));
            }
        }
    }

    function acquire_focus($datebox) {
        $datebox.find('input').focus();
    }

    function scroll_to_see($datebox, old_top) {
        var new_top = $datebox.offset().top;
        var offset = new_top - $(window).scrollTop();
        if (offset < TOP_MARGIN && new_top < old_top) {
            $('html,body').animate({
                scrollTop: new_top - TOP_MARGIN
            }, SCROLLING_TIME);
        } else if (offset + BOTTOM_MARGIN > window.innerHeight &&
                    new_top > old_top) {
            $('html,body').animate({
                scrollTop: new_top + BOTTOM_MARGIN - window.innerHeight
            }, SCROLLING_TIME);
        }
    }

    function set_timeline_height() {
        var dateboxLength = $timeline.find('.oioioi-timeline__datebox')
            .length;
        timeline_height = Math.max(timeline_height,
            dateboxLength * DATEBOX_HEIGHT);
        $timeline.css('height', timeline_height);
        $timeline.find('.oioioi-timeline__round-group')
            .css('height', timeline_height);
    }

    function init() {

        // add some more HTML
        create_now_bar();
        create_connectors();
        create_round_bars();
        create_lines();
        create_hint();
        assign_colors();

        set_timeline_height();

        // init datepickers
        $timeline.find('.date').each(function () {
            initDateTimePicker(this)
        })
        
        // connect equal dates
        create_groups();

        // update positions
        change_date_handler();

        // adjust y position and date range on date change
        $timeline
            .find('.oioioi-timeline__datebox')
            .on('change.td', function(e) {
                if(!e.isValid)
                    return

                var $this = $(this);
                var old_top = $this.offset().top;
                set_group_date($this, e.date);
                change_date_handler();

                // Don't scroll down to an empty datebox
                if (get_date($this) !== null) {
                    scroll_to_see($this, old_top);
                    acquire_focus($this);
                }
            });

        // set click events
        $timeline
            .find('.oioioi-timeline__round-group')
            .on('click', function() {
                var $this = $(this);
                if ($this.hasClass(UNDIM_CLASS)) {
                    // undim all groups
                    change_dim_state(false);
                } else {
                    // dim all groups but this one
                    change_dim_state(true);
                    $this.removeClass(DIM_CLASS);
                    $this.addClass(UNDIM_CLASS);
                    change_group_state($this, false);
                }
            });

        $timeline
            .find('.oioioi-timeline__datebox')
            .on('click', function(e) {
                e.stopPropagation();
            });

        $timeline_form.find('.btn-reset').on('click', function() {
            location.reload();
        });

        $timeline_form.submit(function() {
            $timeline.find('input').prop('disabled', false);
        });

        $timeline
            .find('.oioioi-timeline__group-delete-btn')
            .on('click', function() {
                var $datebox = $(this)
                    .parents('.oioioi-timeline__datebox');
                if ($datebox.hasClass('oioioi-timeline__datebox-group')) {
                    split_group($datebox);
                    change_date_handler();
                }
            });

        $timeline.find('input').keypress(function(e) {
            // we don't want Enter keypress to cause form submission
            // let it update datebox layout instead
            if (e.key === 'Enter') {
                e.preventDefault();
                e.target.dispatchEvent(new Event('change'));
            }
        });

        document.onkeydown = custom_undo;
    }

    init();
})