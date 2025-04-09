import "jqtree"

window.init_portal_tree = function(portal_url, move_url) {
    $('#tree').tree({
        autoOpen: true,
        dragAndDrop: true,
        selectable: false,
        onCanMove: function(node) {
            return !!node.parent.parent;
        },
        onCanMoveTo: function(node, target, position) {
            var newParent;
            if(position == 'inside')
                newParent = target;
            else
                newParent = target.parent;

            if(!newParent.parent)
                return false;

            if(newParent == node.parent)
                return true;

            for(var i = 0; i < newParent.children.length; ++i)
                if(newParent.children[i].short_name == node.short_name)
                    return false;

            return true;
        }
    }).bind('tree.click', function(event) {
        var path = '';
        var node = event.node;
        while(node.parent && node.parent.parent) {
            path = node.short_name + '/' + path;
            node = node.parent;
        }
        var url = portal_url.replace(/__PATH__/g, path);
        window.location.href = url;
    }).bind('tree.move', function(event) {
        $.ajax(move_url, {
            data: {
                node: event.move_info.moved_node.id,
                target: event.move_info.target_node.id,
                position: event.move_info.position
            }
        });
    });
}