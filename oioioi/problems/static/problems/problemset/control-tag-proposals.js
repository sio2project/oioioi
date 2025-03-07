document.addEventListener("DOMContentLoaded", function(){
    var checkbox = document.getElementById("show-tag-proposals-checkbox");
    if (checkbox) {
        var proposals = document.querySelectorAll(".aggregated-proposals");
        function toggleProposals() {
            proposals.forEach(function(div){
                div.style.display = checkbox.checked ? "inline-block" : "none";
            });
        }
        checkbox.addEventListener("change", toggleProposals);
        toggleProposals(); // on page load
    }
});
