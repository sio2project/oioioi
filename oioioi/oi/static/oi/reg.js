$(document).ready(function() {
    var province, city, school;
    if ($('#id_school').length > 0) { /* user registration form */
        province = $('#id_school_province');
        city = $('#id_school_city');
        school = $('#id_school');
    } else { /* admin.StackedInline registration form */
        province = $('#id_oi_oiregistration-0-school_province');
        city = $('#id_oi_oiregistration-0-school_city');
        school = $('#id_oi_oiregistration-0-school');
    }
    province.change(function() {
        city.html('');
        school.html('');
        if (province.val()) {
            $.get(oioioi_base_url + 'oi/cities',
                {'province': province.val()},
                function(options) { city.html(options); })
        }
    });
    city.change(function() {
        school.html('');
        if (province.val() && city.val()) {
            $.get(oioioi_base_url + 'oi/schools',
                {'province': province.val(), 'city': city.val()},
                function(options) { school.html(options); })
        }
    });
});
