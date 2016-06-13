(function() {
    "use strict";

    var attachments = new Attachments();
    var tags = new Tags();

    $(document).ready(function() {
        attachments.bindActions();
        tags.bindActions();
    });
}());