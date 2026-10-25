// Load right after highcharts/highcharts.js.
//
// Not in a common/ directory on purpose: {% common_scripts %} loads every
// common/*.js file on every page, where Highcharts is not defined.
//
// Highcharts 13 follows the OS color scheme by default (palette.colorScheme
// 'light dark'). OIOIOI has its own dark mode (darkreader, toggled in the UI, see
// base/static/js/darkreader.js), so keep charts light and let darkreader recolor
// them, as with Highcharts 12.
Highcharts.setOptions({
    palette: {
        colorScheme: 'light',
    },
});
