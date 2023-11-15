$(function() {
    // DOM elements
    const navbar = $('#main-navbar');
    const navbarFlexSpace = $('.oioioi-navbar__flex');

    const countdownTime = $('#countdown-time');
    const countdownProgress = $('#countdown-progress');
    const countdownProgressFill = countdownProgress.find('.progress-bar');
    const countdownProgressText = countdownProgressFill.find('span');

    const clock = $('#clock');
    const adminClock = $('#admin-clock');
    const adminTime = $('#admin-time');
    const adminTimeLabel = $('#admin-time-label');

    // Constants
    const CACHE_DETECT_TIME = 3000;
    const DISPLAY_TIME = 10;
    // Should match scss `$countdown-time-full-width` property
    const FULL_TEXT_WIDTH = 550;

    // Enum to indicate countdown display type
    const CountdownType = {
        NONE: 0,
        PROGRESS: 1,
        TEXT: 2
    };

    // Duration of current round (in seconds)
    let roundDuration;
    // Round name
    let roundName;
    // Date until we countdown to
    let countdownDate;

    // Current timestamp (milliseconds)
    let timestamp;
    // Time calculated in previous `update()` call
    let previousUserTime;

    // Indicates whether user has privileges to change time
    let isTimeAdmin;
    // Indicates whether the time has been changed by admin
    let isAdminTimeSet;
    // Delay (in seconds) between the actual time and the one set by admin
    let delay = 0;

    /**
     * Updates clock and progress bar.
     * Called every second.
     */
    function update() {
        // If we detect a long time interval between subsequent
        // `update()` calls, we detect a cached version of the page
        // and send a request to resynchronize time with server
        let userTime = new Date().getTime();
        if (previousUserTime !== null
                && userTime - previousUserTime > CACHE_DETECT_TIME) {
            $(window).trigger('updateStatusRequest');
        }
        previousUserTime = userTime;

        updateClockTime(new Date(userTime + delay));

        timestamp = userTime + delay;
        const remainingSeconds = countdownDate - Math.floor(timestamp / 1000);

        updateCountdown(remainingSeconds);
    }

    /**
     * Coverts datetime object into YYYY-MM-DD HH:mm:ss string
     * @param time: Date
     * @returns {string} formatted date
     */
    function getDatetimeString(time) {
        function twoDigit(number) {
            return ("0" + number).slice(-2);
        }

        return time.getFullYear() + '-' + twoDigit(time.getMonth() + 1) + '-'
            + twoDigit(time.getDate()) + ' ' + twoDigit(time.getHours()) + ':'
            + twoDigit(time.getMinutes()) + ':' + twoDigit(time.getSeconds());
    }

    /**
     * Updates the text in #clock node
     * @param time: Date
     */
    function updateClockTime(time) {
        clock.text(time.toLocaleTimeString());
    }

    /**
     * Updates countdown text and progress fill
     * @param remainingSeconds: number
     */
    function updateCountdown(remainingSeconds) {
        const countdownParams = getCountdownParams(remainingSeconds);

        // Hide elements and exit
        if (countdownParams.countdownType === CountdownType.NONE) {
            countdownTime.css('visibility', 'hidden');
            countdownProgressFill.css('visibility', 'hidden');
            return;
        }

        // Show countdown text
        countdownTime.css('visibility', 'visible');
        const flexSpaceAvailable = navbarFlexSpace.width() * 2;
        const spaceAvailable = countdownTime.width() + flexSpaceAvailable;

        if (spaceAvailable > FULL_TEXT_WIDTH) {
            countdownTime.text(countdownParams.countdownText);
        } else {
            countdownTime.text(countdownParams.countdownShort);
        }

        // If text only hide progress and exit
        if (countdownParams.countdownType === CountdownType.TEXT) {
            countdownProgressFill.css('visibility', 'hidden');
            return;
        }

        // Show countdown progress
        countdownProgressFill.css('visibility', 'visible');
        const completion = 1 - remainingSeconds / roundDuration;

        countdownProgressFill.width((completion * 100) + '%');
        countdownProgressFill.attr('aria-valuenow',
            Math.floor(completion * 100));
        countdownProgressText.text(Math.floor(completion * 100) + "%");

        if (completion < 0.5) {
            countdownProgressFill.removeClass('bg-warning');
            countdownProgressFill.removeClass('bg-danger');
        } else if (completion < 0.8) {
            countdownProgressFill.removeClass('bg-danger');
            countdownProgressFill.addClass('bg-warning');
        } else {
            countdownProgressFill.removeClass('bg-warning');
            countdownProgressFill.addClass('bg-danger');
        }
    }

    /**
     * Starts up the clock interval.
     */
    let updateClockInterval = null;
    function startClock() {
        clearInterval(updateClockInterval);
        updateClockInterval = setInterval(function() {
            if (isAdminTimeSet) {
                clearInterval(updateClockInterval);
                updateClockInterval = null;
            } else {
                update();
            }
        }, 1000);
    }

    /**
     * Creates datetime string accepted by #admin-time input
     * @param time: Date
     * @returns {string} datetime in format (yyyy-mm-dd hh:mm:ss)
     */
    function getAdminTimeFormat(time) {
        return time.getFullYear() +
        "-" + ("0" + (time.getMonth() + 1)).slice(-2) +
        "-" + ("0" + time.getDate()).slice(-2) +
        " " + ("0" + time.getHours()).slice(-2) +
        ":" + ("0" + time.getMinutes()).slice(-2) +
        ":" + ("0" + time.getSeconds()).slice(-2);
    }

    /**
     * Sets admin clock click event listener to update admin time change
     * input to the current time.
     */
    function setAdminClockClickListener() {
        if (!adminClock) {
            return;
        }

        adminClock.on('click', function() {
            let adminTimeValue = null;
            if (isAdminTimeSet) {
                adminTimeValue = new Date(timestamp);
            } else {
                adminTimeValue = new Date(new Date().getTime() + delay);
            }
            adminTime.val(getAdminTimeFormat(adminTimeValue));
        });
    }

    /**
     * Calculates user local variables based on server response.
     * @param data Server response data
     */
    function synchronizeTime(data) {
        isAdminTimeSet = data.is_admin_time_set;
        timestamp = data.time * 1000;

        const newDelay = timestamp - new Date().getTime();
        if (Math.abs(newDelay - delay) > 1000) {
            delay = newDelay;
        }

        const startDate = data.round_start_date;
        const endDate = data.round_end_date;

        if (endDate) {
            countdownDate = endDate;
            roundDuration = endDate - startDate;
        } else if (startDate) {
            countdownDate = startDate;
            roundDuration = null;
        }

        roundName = data.round_name;
    }

    /**
     * Calculates admin local variables based on server response.
     * @param data Server response data
     */
    function synchronizeAdminTime(data) {
        isAdminTimeSet = data.is_admin_time_set;
        const time = new Date(data.time * 1000);

        if (isAdminTimeSet) {
            update();
            clock.text(getDatetimeString(time));
            navbar.addClass('navbar-admin-time');
            adminTimeLabel.removeClass('hidden');
        } else if (navbar.hasClass('navbar-admin-time')) {
            startClock();
            navbar.removeClass('navbar-admin-time');
            adminTimeLabel.addClass('hidden');
        }
    }

    /**
     * Calculates countdown type (display mode NONE|PROGRESS|TEXT), and text
     * to display in `countdownTime` (with short version for smaller devices).
     * @param remainingSeconds
     * @returns {{countdownType, countdownText, countdownShort}}
     */
    function getCountdownParams(remainingSeconds) {
        let countdownType = CountdownType.NONE;
        let countdownText = '';
        let countdownShort = '';

        if (remainingSeconds >= -DISPLAY_TIME) {
            let countdown = remainingSeconds;
            let countdownDestination;
            let countdownDestinationShort;

            if (roundDuration) {
                countdownDestination = gettext(
                "end of the %(round_name)s").fmt({
                    round_name: roundName
                });
                countdownDestinationShort = gettext("to the end");
                countdownType = CountdownType.PROGRESS;
            } else {
                countdownDestination = gettext(
                "start of the %(round_name)s").fmt({
                    round_name: roundName
                });
                countdownDestinationShort = gettext("to the start");
                countdownType = CountdownType.TEXT;
            }

            // Save text for seconds
            const seconds = countdown % 60;
            const secondsText = ngettext(
            "%(seconds)s second ",
            "%(seconds)s seconds ",
            seconds).fmt({
                seconds: seconds
            });
            const secondsShortText = gettext("%(seconds)ss ")
                .fmt({ seconds: seconds });

            // Save text for minutes
            countdown = Math.floor(countdown / 60);
            const minutes = countdown % 60;
            const minutesText = ngettext(
            "%(minutes)s minute ",
            "%(minutes)s minutes ",
            minutes).fmt({
                minutes: minutes
            });
            const minutesShortText = gettext("%(minutes)sm ")
                .fmt({ minutes: minutes });

            // Save text for hours
            countdown = Math.floor(countdown / 60);
            const hours = countdown % 24;
            const hoursText = ngettext(
            "%(hours)s hour ", "%(hours)s hours ",
            hours).fmt({
                hours: hours
            });
            const hoursShort = gettext("%(hours)sh ")
                .fmt({ hours: hours });

            // Save text for days
            countdown = Math.floor(countdown / 24);
            const days = countdown;
            const daysText = ngettext(
            "%(days)s day ",
            "%(days)s days ",
            days).fmt({
                days: days
            });
            const daysShort = gettext("%(days)sd ")
                .fmt({ days: days });

            if (days > 0) {
                const countdownDays = daysText + hoursText + minutesText
                    + secondsText;
                countdownShort = daysShort + hoursShort + minutesShortText
                    + secondsShortText + countdownDestinationShort;
                countdownText = ngettext(
                "%(countdown_days)sleft to the %(countdown_destination)s.",
                "%(countdown_days)sleft to the %(countdown_destination)s.",
                days).fmt({
                    countdown_days: countdownDays,
                    countdown_destination: countdownDestination,
                    round_name: roundName
                });
            } else if (hours > 0) {
                const countdownHours = hoursText + minutesText + secondsText;
                countdownShort = hoursShort + minutesShortText
                    + secondsShortText + countdownDestinationShort;
                countdownText = ngettext(
                "%(countdown_hours)sleft to the %(countdown_destination)s.",
                "%(countdown_hours)sleft to the %(countdown_destination)s.",
                hours).fmt({
                    countdown_hours: countdownHours,
                    countdown_destination: countdownDestination
                });
            } else if (minutes > 0) {
                const countdownMinutes = minutesText + secondsText;
                countdownShort = minutesShortText + secondsShortText
                    + countdownDestinationShort;
                countdownText = ngettext(
                "%(countdown_minutes)sleft to the %(countdown_destination)s.",
                "%(countdown_minutes)sleft to the %(countdown_destination)s.",
                minutes).fmt({
                    countdown_minutes: countdownMinutes,
                    countdown_destination: countdownDestination
                });
            } else if (seconds >= 0) {
                const countdownSeconds = secondsText;
                countdownShort = secondsShortText + countdownDestinationShort;
                countdownText = ngettext(
                "%(countdown_seconds)sleft to the %(countdown_destination)s.",
                "%(countdown_seconds)sleft to the %(countdown_destination)s.",
                seconds).fmt({
                    countdown_seconds: countdownSeconds,
                    countdown_destination: countdownDestination
                });
            } else if (roundDuration) {
                countdownText = gettext("The round is over!");
                countdownType = CountdownType.PROGRESS;
                countdownShort = countdownText;
            } else {
                countdownText = gettext("The round has started!");
                countdownType = CountdownType.TEXT;
                countdownShort = countdownText;
            }
        }

        return {
            countdownType: countdownType,
            countdownText: countdownText,
            countdownShort: countdownShort
        };
    }

    /* Initialize event listeners */

    setAdminClockClickListener();

    $(window).one('initialStatus', function(event, data) {
        isTimeAdmin = data.is_time_admin;
        synchronizeTime(data);
        update();
        startClock();

        if (isTimeAdmin) {
            synchronizeAdminTime(data);
        }
    });

    $(window).on('updateStatus', function(event, data) {
         if ('time' in data) {
            synchronizeTime(data);

            if (isTimeAdmin) {
                synchronizeAdminTime(data);
            }
        }
    });
});
