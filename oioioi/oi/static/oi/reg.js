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

    function get_school_info() {
        if (school.val()) {
            $.get(oioioi_base_url + 'oi/school/',
                {'school': school.val()},
                function(info) {
                    $("#school_info_wrapper").html(info);
                }
            );
        }
    }

    if(province.val() === "") {
        city.prop('disabled', true);
        school.prop('disabled', true);
    }

    if(city.val() === "") {
        school.prop('disabled', true);
    }

    if (school.val() !== "") {
        get_school_info();
    }

    province.change(function() {
        city.html('');
        city.prop('disabled', true);
        school.html('');
        school.prop('disabled', true);
        if (province.val()) {
            $.get('oicities/',
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
            $.get('oischools/',
                {'province': province.val(), 'city': city.val()},
                function(options) {
                    school.html(options);
                    school.prop('disabled', false);
                });
        }
    });

    school.change(function() {
        if (school.val()) {
            get_school_info();
        }
        else {
            $("#school_info_wrapper").html("");
        }
    });

    if (province.val()) {
        previous_city = city.val();
        $.get('oicities/',
                {'province': province.val()},
                function(options) {
                    city.html(options);
                    $(city.selector + ' option[value="' + previous_city + '"]').attr('selected', 'selected');
                });
    }
    if (province.val() && city.val()) {
        previous_school = school.val();
        $.get('oischools/',
                {'province': province.val(), 'city': city.val()},
                function(options) {
                    school.html(options);
                    $(school.selector + ' option[value="' + previous_school + '"]').attr('selected', 'selected');
                });
    }
});
