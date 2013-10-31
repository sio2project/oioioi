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

    if(province.val() === "") {
        city.prop('disabled', true);
        school.prop('disabled', true);
    }

    if(city.val() === "") {
        school.prop('disabled', true);
    }

    province.change(function() {
        city.html('');
        city.prop('disabled', true);
        school.html('');
        school.prop('disabled', true);
        if (province.val()) {
            $.get(oioioi_base_url + 'oi/cities/',
                {'province': province.val()},
                function(options) {
                    city.html(options);
                    city.prop('disabled', false);
                });
        }
    });

    city.change(function() {
        school.html('');
        school.prop('disabled', true);
        if (province.val() && city.val()) {
            $.get(oioioi_base_url + 'oi/schools/',
                {'province': province.val(), 'city': city.val()},
                function(options) {
                    school.html(options);
                    school.prop('disabled', false);
                });
        }
    });
});
