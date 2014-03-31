$(function() {
    if (window.File && window.FileList && window.FileReader) {

        if (!$('#ddzone')) {
            return;
        }

        $('.wrapper').on('dragover', ShowDdzone);
        // prevent opening in browser file dropped not in drop area
        $('#ddzone').on('drop', HideDdzone);
        $('#droparea').on('dragover', DropAreaHover);
        $('#droparea').on('dragleave', DropAreaHover);
        $('#droparea').on('drop', DropedFileHandler);
        $('#ddzone').on('click', HideDdzone);
        $('#ddzone').on('dragleave', HideDdzone);
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
    // do not even show ddzone for elements of window
    if (e.originalEvent.dataTransfer.types.indexOf('Files') == -1) {
        return;
    }
    $('#droparea').removeClass().html(gettext("Drop file here"));
    $('#ddzone').show();
}

function HideDdzone(e) {
    e.stopPropagation();
    e.preventDefault();
    filedragHide();
}

function filedragHide() {
    $('#ddzone').fadeOut(200);
}

function filedragNotifyErr(message) {
    $('#droparea').removeClass('hover').addClass('error');
    $('#droparea').html(message);
    setTimeout(filedragHide, 1500);
}

// file selection
function DropedFileHandler(e) {
    e.stopPropagation();
    // necessary to prevent opening file dropped outside the drop area
    e.preventDefault();

    // fetch FileList object
    org = e.originalEvent;
    var files = org.target.files || org.dataTransfer.files;

    if (files.length != 1) {
        filedragNotifyErr(gettext("Aborted! Drop one file."));
        return;
    }
    if (files[0].size == 0) {
        filedragNotifyErr(gettext("Aborted! Empty file dropped."));
        return;
    }
    // Size in bytes (characters)
    if (files[0].size > 61440) {
        filedragNotifyErr(gettext("Aborted! Too big file dropped."));
        return;
    }
    if (files[0].type && !files[0].type.match('text.*')) {
        filedragNotifyErr(gettext("Aborted! Drop a valid text file."));
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
