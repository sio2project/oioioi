$(function() {
    const problemInstanceSelector = $("#id_problem_instance_id");

    function findParents(fg) {
        return fg.closest("div");
    }

    function showFieldGroup(fg) {
        findParents(fg).show();
    }

    function hideFieldGroup(fg) {
        findParents(fg).hide();
    }

    function setFormToProblemInstance(problemInstanceId) {
        // We exclude fields that show regardless of task type (marked with always),
        // so that we don't hide them.
        const allFields = $("form [data-submit][data-submit!='always']");
        const customFields = $("form [data-submit='" + problemInstanceId + "']");
        if (customFields.length) {
            // found custom div
            hideFieldGroup(allFields);
            showFieldGroup(customFields);
        } else {
            // custom div not found, fall back to default
            const defaultFields = $("form [data-submit='default']");
            hideFieldGroup(allFields);
            showFieldGroup(defaultFields);
        }
    }

    problemInstanceSelector.on('change', function(event) {
        setFormToProblemInstance(event.target.value);
    });

    setFormToProblemInstance(problemInstanceSelector.val());
});
