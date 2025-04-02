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
                // If checkbox is checked, add a parameter to tell the server to include algorithm tag proposals
                if (checkbox.checked) {
                    var includeProposalsInput = document.createElement("input");
                    includeProposalsInput.type = "hidden";
                    includeProposalsInput.name = "include_proposals";
                    includeProposalsInput.value = "1";
                    searchForm.appendChild(includeProposalsInput);
                }
            });
        }

        checkbox.addEventListener("change", toggleProposals);
        toggleProposals(); // on page load
    }
});
