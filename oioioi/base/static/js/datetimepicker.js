// Code for the DateTimePicker django widget
import { TempusDominus } from '@eonasdan/tempus-dominus'

$('.datetimepicker').each(function () {
    new TempusDominus(this ,{
        localization: {
            format: 'yyyy-MM-dd HH:mm',
        }
    })
})