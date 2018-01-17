var ddzone_hide_timeout = null;

$(function() {
    if (window.File && window.FileList && window.FileReader) {

        const dropZoneArea = $('#drop-zone-area');

        if (!dropZoneArea) {
            return;
        }

        $('html')
            .on('dragover', ShowDdzone)
            .on('dragleave', HideDdzone)
            // Prevent opening files dropped outside drop area.
            .on('drop', HideDdzone);


        $('input[type=file]')
            .on('dragover', DdzoneException)
            .on('drop', DdzoneException);

        dropZoneArea
            .on('dragover', ShowDdzone)
            .on('dragover', DropAreaHover)
            .on('dragleave', HideDdzone)
            .on('dragleave', DropAreaHover)
            .on('drop', DropedFileHandler);
    }
});

// file drag hover
function DropAreaHover(e) {
    e.stopPropagation();
    e.preventDefault();

    const dropZoneDisplayedContent = $('#drop-zone-displayed-content');

    if (e.type == 'dragover') {
        dropZoneDisplayedContent.addClass('drop-zone__message--hover');
    } else {
        dropZoneDisplayedContent
            .removeClass('drop-zone__message--hover')
            .removeClass('drop-zone__message--error');
    }
}

function ShowDdzone(e) {
    e.stopPropagation();
    // necessary to prevent opening file dropped outside drop area
    e.preventDefault();

    // Do not show drag-and-drop if not dropping files.
    // This explicit loop is needed on Firefox, where types is not
    // an array, but an object.
    const types = e.originalEvent.dataTransfer.types;
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

    $('#drop-zone-displayed-content')
        .removeClass('drop-zone__message--hover')
        .removeClass('drop-zone__message--error');

    $('#drop-zone-area').show();
    clearTimeout(ddzone_hide_timeout);
}

function DdzoneException(e) {
    e.stopPropagation();
}

function HideDdzone(e) {
    e.stopPropagation();
    e.preventDefault();
    filedragHide();
    $('#drop-zone-displayed-content').html(gettext("Drop file here"));
}

function filedragHide() {
    ddzone_hide_timeout = setTimeout(function() {
        $('#drop-zone-area').hide();
    }, 100);
}

function filedragNotifyErr(message) {
    $('#drop-zone-displayed-content')
        .removeClass('drop-zone__message--hover')
        .addClass('drop-zone__message--error')
        .html(message);

    setTimeout(filedragHide, 1500);
}

// file selection
function DropedFileHandler(e) {
    e.stopPropagation();
    // necessary to prevent opening file dropped outside the drop area
    e.preventDefault();

    // fetch FileList object
    const org = e.originalEvent;
    const files = org.target.files || org.dataTransfer.files;

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
    const reader = new FileReader();
    reader.onload = function(e) {
        $('#dropped-solution').val(e.target.result);
        $('#dropped-solution-name').val(file.name);
        $('#upload').submit();
    };
    reader.readAsText(file);
}