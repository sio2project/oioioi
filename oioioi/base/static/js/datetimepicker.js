// Code for the DateTimePicker django widget
import { TempusDominus } from '@eonasdan/tempus-dominus'

export function initDateTimePicker(element) {
    const picker = new TempusDominus(element, {
        localization: {
            format: 'yyyy-MM-dd HH:mm',
            locale: Cookies.get("lang") || "en",
        },
        display: {
            theme: 'light',
        }
    })

    // store the TempusDominus instance for easy access
    $(element).data('TempusDominus', picker);
}

$('.datetimepicker').each(function () {
    initDateTimePicker(this)
})