$(function(){
/*
    Script for 'collapsibles' with asynchronously loadable data.
    After first load everything behaves like in Bootstrap.
    Trigerrer: data-async-toggle="collapse" data-bs-target="`JQuery selector`"
    Dynamic collapsible: class="collapse" data-loadurl="http://url/with/html"
*/
    $('body').on('click', '.btn[data-async-toggle=collapse]', function() {
        var e = $(this);

        //All buttons triggerring same location
        var s = $('.btn[data-async-toggle=collapse][data-bs-target=' +
                  e.data('bs-target')+']');
        s.each(function() {
            var e = $(this);
            e.removeAttr('data-async-toggle');
            var span = $('span', this); // icon
            e.data('prev-icon', span.prop('class'));
            span.removeClass(e.data('prev-icon'));

            e.toggleClass('loading disabled');
            span.addClass('fa-solid fa-rotate-right');
        });

        var t = $(e.data('bs-target'));
        t.load(t.data('loadurl'), function(response, status) {
            if (status == "error") {
                t.html('<div class="alert alert-danger"><pre>' + response +
                       '</pre></div>');
            }
            t.collapse('show');
            s.each(function(){
                var e = $(this);
                var span = $('span', this);
                e.attr('data-bs-toggle', 'collapse');
                e.toggleClass('loading disabled');
                span.prop('class', e.data('prev-icon'));
            });
        });


    });
});
