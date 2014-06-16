var ddzone_hide_timeout = null;

$(function() {
    if (window.File && window.FileList && window.FileReader) {

        if (!$('#ddzone')) {
            return;
        }

        $('html').on('dragover', ShowDdzone);
        // prevent opening in browser file dropped not in drop area
        $('html').on('drop', HideDdzone);
        $('input[type=file]').on('dragover', DdzoneException);
        $('input[type=file]').on('drop', DdzoneException);
        $('#ddzone').on('dragover', ShowDdzone);
        $('#droparea').on('dragover', ShowDdzone);
        $('#droparea').on('dragover', DropAreaHover);
        $('#droparea').on('dragleave', DropAreaHover);
        $('#droparea').on('drop', DropedFileHandler);
        $('html').on('dragleave', HideDdzone);
    }
});

// file drag hover
function DropAreaHover(e) {
    e.stopPropagation();
    e.preventDefault();
    if ( e.type == 'dragover' ) {
        $('#droparea').addClass('hover');
    } else {
        $('#droparea').removeClass();
    }
}

function ShowDdzone(e) {
    e.stopPropagation();
    // necessary to prevent opening file dropped outside drop area
    e.preventDefault();

    // Do not show drag-and-drop if not dropping files.
    // This explicit loop is needed on Firefox, where types is not
    // an array, but an object.
    var types = e.originalEvent.dataTransfer.types;
    var has_file = false;
    console.log(types);
    for (var i = 0; i < types.length; i++) {
        if (types[i] == 'Files') {
            has_file = true;
            break;
        }
    }
    if (!has_file) {
        return;
    }

    $('#droparea').removeClass()
    $('#dropmsg').html(gettext("Drop file here"));
    $('#ddzone').show();
    clearTimeout(ddzone_hide_timeout);
}

function DdzoneException(e) {
    e.stopPropagation();
}

function HideDdzone(e) {
    e.stopPropagation();
    e.preventDefault();
    filedragHide();
}

function filedragHide() {
    ddzone_hide_timeout = setTimeout(function() {
        $('#ddzone').hide();
    }, 100);
}

function filedragNotifyErr(message) {
    $('#droparea').removeClass('hover').addClass('error');
    $('#dropmsg').html(message);
    setTimeout(filedragHide, 1500);
}

// file selection
function DropedFileHandler(e) {
    e.stopPropagation();
    // necessary to prevent opening file dropped outside the drop area
    e.preventDefault();

    // fetch FileList object
    var org = e.originalEvent;
    var files = org.target.files || org.dataTransfer.files;

    if (files.length != 1) {
        filedragNotifyErr(gettext("Drop one file."));
        return;
    }
    if (files[0].size == 0) {
        filedragNotifyErr(gettext("File is empty."));
        return;
    }
    // Size in bytes (characters)
    if (files[0].size > 61440) {
        filedragNotifyErr(gettext("File too big."));
        return;
    }
    if (files[0].type && !files[0].type.match('text.*')) {
        filedragNotifyErr(gettext("Not a text file."));
        return;
    }

    filedragParseFile(files[0]);
}

// output file information
function filedragParseFile(file) {
    var reader = new FileReader();
    reader.onload = function(e) {
        $('#dropped_solution').val(e.target.result);
        $('#dropped_solution_name').val(file.name);
        $('#upload').submit();
    }
    reader.readAsText(file);
}
