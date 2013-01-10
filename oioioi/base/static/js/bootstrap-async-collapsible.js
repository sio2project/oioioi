$(function(){
/*
    Script for 'collapsibles' with asynchronously loadable data.
    After first load everything behaves like in Bootstrap.
    Trigerrer: data-async-toggle="collapse" data-target="`JQuery selector`"
    Dynamic collapsible: class="collapse" data-loadurl="http://url/with/html"
*/
$('.btn[data-async-toggle=collapse]').bind('click.async-toggle', function() {
    var e = $(this);

    //All buttons triggerring same location
    var s = '.btn[data-async-toggle=collapse][data-target='+e.data('target')+']';
    $(s).each(function() {
        var e = $(this);
        e.unbind('click.async-toggle');
        var i = $('i', this); // icon
        e.data('prev-icon', i.prop('class'));
        i.removeClass(e.data('prev-icon'));

        e.toggleClass('loading disabled');
        i.addClass('icon-refresh');
    });

    var t = $(e.data('target'));
    t.load(t.data('loadurl'), function(response, status) {
        if (status == "error") {
            t.html('<div class="alert alert-error"><pre>' + response
                + '</pre></div>');
        }
        t.collapse('show');
        $(s).click(function(ev) {                   // Bind standard behaviour
            ev.preventDefault();
            t.collapse('toggle');
        });
        $(s).each(function(){
            var e = $(this);
            var i = $('i', this);
            e.toggleClass('loading disabled');
            i.prop('class', e.data('prev-icon'));
        });
    });


});
});
