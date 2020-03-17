/**
 * Works in submit view in order to properly show (and hide) fields based on a
 * given problem instance.
 * @param {Array<number>} default_fields_pi_ids contains ids of submittable
 * problem instances that want to show default fields
 */
function startShowingFields(hide_default_fields_pi_ids) {
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
        const defaultFields = $("form [data-submit='default']");
        const customFields = $("form [data-submit='" + problemInstanceId + "']");
        const hidesDefault = hide_default_fields_pi_ids.includes(parseInt(problemInstanceId, 10));

        hideFieldGroup(allFields);
        if (customFields.length) // found custom div
            showFieldGroup(customFields);
        if (!hidesDefault)
            showFieldGroup(defaultFields);
    }

    problemInstanceSelector.on("change", function(event) {
        setFormToProblemInstance(event.target.value);
    });

    setFormToProblemInstance(problemInstanceSelector.val());
}
