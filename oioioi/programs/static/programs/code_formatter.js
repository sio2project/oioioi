// Adds a toggle to the submission source page that shows the source formatted with clang-format
// (compiled to WebAssembly). Only the displayed code changes, never the submission itself.
import initClangFormat, { format } from '@wasm-fmt/clang-format/web';
import hljs from 'highlight.js/lib/core';
import cpp from 'highlight.js/lib/languages/cpp';
import c from 'highlight.js/lib/languages/c';

hljs.registerLanguage('cpp', cpp);
hljs.registerLanguage('c', c);

const CLANG_FORMAT_STYLE = JSON.stringify({
    BasedOnStyle: 'Chromium',
    IndentWidth: 4,
    ColumnLimit: 80,
});

// Builds the same markup that Pygments generates for the original view (see HtmlFormatter(linenos=True) in
// programs/views.py), so that the site's styles for `.syntax-highlighttable` apply to both views.
function buildFormattedView(formattedSource, language) {
    const lineCount = formattedSource.replace(/\n$/, '').split('\n').length;

    // Pad the numbers with spaces (the box is monospace), so that they are right-aligned: 9 above 10, not next to it.
    const width = String(lineCount).length;
    const numbers = document.createElement('pre');
    for (let i = 1; i <= lineCount; i++) {
        const number = document.createElement('span');
        number.className = 'normal';
        number.textContent = String(i).padStart(width, ' ');
        numbers.append(number, i < lineCount ? '\n' : '');
    }
    const numbersBox = document.createElement('div');
    numbersBox.className = 'linenodiv';
    numbersBox.appendChild(numbers);
    const numbersCell = document.createElement('td');
    numbersCell.className = 'linenos';
    numbersCell.appendChild(numbersBox);

    const code = document.createElement('code');
    code.className = `language-${language}`;
    code.textContent = formattedSource;
    const codePre = document.createElement('pre');
    codePre.appendChild(code);
    hljs.highlightElement(code);
    const codeBox = document.createElement('div');
    codeBox.appendChild(codePre);
    const codeCell = document.createElement('td');
    codeCell.className = 'code';
    codeCell.appendChild(codeBox);

    const row = document.createElement('tr');
    row.append(numbersCell, codeCell);
    const table = document.createElement('table');
    table.className = 'syntax-highlighttable';
    table.appendChild(row);

    const wrapper = document.createElement('div');
    wrapper.className = 'syntax-highlight';
    wrapper.appendChild(table);
    return wrapper;
}

document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('format_btn');
    const sourceView = document.getElementById('source_view');
    const rawSource = document.getElementById('raw_source');
    if (!button || !sourceView || !rawSource) {
        return;
    }

    const originalNodes = Array.from(sourceView.childNodes);
    let formattedView = null;
    let showingFormatted = false;

    function show(nodes) {
        sourceView.replaceChildren(...nodes);
    }

    button.addEventListener('click', async () => {
        if (showingFormatted) {
            show(originalNodes);
            showingFormatted = false;
            button.textContent = button.dataset.labelOriginal;
            return;
        }

        button.disabled = true;
        try {
            if (formattedView === null) {
                await initClangFormat();
                const formatted = format(rawSource.textContent, `main.${button.dataset.language}`, CLANG_FORMAT_STYLE);
                formattedView = buildFormattedView(formatted, button.dataset.language);
            }
            show([formattedView]);
            showingFormatted = true;
            button.textContent = button.dataset.labelFormatted;
        } catch (err) {
            console.error(err);
            alert(button.dataset.labelError);
        } finally {
            button.disabled = false;
        }
    });
});
