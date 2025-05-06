document.addEventListener("DOMContentLoaded", function(){
    var checkbox = document.getElementById("show-tag-proposals-checkbox");
    if (checkbox) {
        var proposals = document.querySelectorAll(".aggregated-proposals");

        function toggleProposals() {
            proposals.forEach(function(div){
                div.style.display = checkbox.checked ? "inline-block" : "none";
            });
        }

        var searchForm = document.getElementById("problemsite_search-form");
        if (searchForm) {
            searchForm.addEventListener("submit", function(event) {
                var control_proposals = document.getElementById("control-include_proposals");
                if (checkbox.checked) {
                    control_proposals.value = "1";
                } else {
                    control_proposals.value = "0";
                }
            });
        }

        // Intercept clicks on tag labels and origininfo labels
        document.querySelectorAll("a.tag-label").forEach(function(link) {
            link.addEventListener("click", function(event) {
                if (checkbox.checked) {
                    event.preventDefault();
                    var url = new URL(link.href, window.location.origin);
                    url.searchParams.set("include_proposals", "1");
                    window.location.href = url.toString();
                }
            });
        });

        checkbox.addEventListener("change", toggleProposals);
        toggleProposals(); // on page load
    }
});
