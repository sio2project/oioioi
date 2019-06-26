$(function() {
    const regexp_contest = "id_contestcompiler_set-\\d+-language";
    const regexp_problem = "id_problemcompiler_set-\\d+-language";
    const to_add = gettext("Here you can override default compilers for problems in this contest");
    const new_id = "id_contestcompiler_additionalinfo";

    $("#id_contestcompiler_set-TOTAL_FORMS").before($("<div></div>", {id: new_id, text: to_add}));

    $("fieldset").on("input", "select", function() {
        if ($(this).attr("id")) {
            var type = "";
            if ($(this).attr("id").match(regexp_contest)) {
                type = "contest";
            }
            if ($(this).attr("id").match(regexp_problem)) {
                type = "problem";
            }
            if (type != "") {
                if ($(this).val()) {
                    const hints_url = $(this).data("compilerchoicesurl");
                    const parts = $(this).attr("id").split("-");
                    const compiler_select_id = "id_" + type +  "compiler_set-" + parts[1] + "-compiler";
                    var compiler_select = $("#" + compiler_select_id);
                    $.getJSON(hints_url, {language : $(this).val()}).done(
                        function(json){
                            compiler_select.empty();
                            $.each(json, function(index, option) {
                                compiler_select.append($("<option></option>").attr("value", option).text(option));
                            });
                        }).fail(function(jqxhr, textStatus, error){
                            $("label[for='" + compiler_select_id + "']").html(gettext("Compiler") + " <font color='red'>" + gettext("Failed to fetch available compilers" + "</font>"));
                            var err = textStatus + ", " + error;
                    });
                }
            }
        }
    });

});

