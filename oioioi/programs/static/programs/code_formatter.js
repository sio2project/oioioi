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

// Splits a text node around the parts matched by `regex` and wraps those parts in <span class="className">.
// `pick` returns the [start, end) range of the text to wrap inside a match.
function wrapMatches(node, regex, className, pick) {
    const text = node.data;
    const fragment = document.createDocumentFragment();
    let last = 0;
    for (const match of text.matchAll(regex)) {
        const [start, end] = pick(match);
        fragment.append(text.slice(last, start));
        const span = document.createElement('span');
        span.className = className;
        span.textContent = text.slice(start, end);
        fragment.append(span);
        last = end;
    }
    if (last > 0) {
        fragment.append(text.slice(last));
        node.replaceWith(fragment);
    }
}

// highlight.js does not mark everything that Pygments does, so mark the bold parts of the
// Pygments style here: escape sequences in strings and names after `namespace` / `typename`.
function addPygmentsLikeMarks(code) {
    const textNodes = [];
    const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }
    const nameAfterKeyword = /^\s*[A-Za-z_]\w*/g;
    const wholeName = (match) => [match[0].search(/\S/), match[0].length];
    for (const node of textNodes) {
        const parent = node.parentElement;
        const previous = node.previousSibling;
        if (parent.classList.contains('hljs-string') && parent.textContent.startsWith('"')) {
            wrapMatches(node, /\\(?:x[0-9a-fA-F]{1,2}|[0-7]{1,3}|[\s\S])/g, 'hljs-escape', (m) => [m.index, m.index + m[0].length]);
        } else if (previous?.classList?.contains('hljs-keyword')) {
            if (previous.textContent === 'namespace') {
                wrapMatches(node, nameAfterKeyword, 'hljs-namespace', wholeName);
            } else if (previous.textContent === 'typename') {
                wrapMatches(node, nameAfterKeyword, 'hljs-title class_', wholeName);
            }
        }
    }
}

// Builds the same markup that Pygments generates for the original view (see HtmlFormatter(linenos=True) in
// programs/views.py), so that the site's styles for `.syntax-highlighttable` apply to both views.
function buildFormattedView(formattedSource) {
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
    code.className = 'language-cpp';
    code.textContent = formattedSource;
    const codePre = document.createElement('pre');
    codePre.appendChild(code);
    hljs.highlightElement(code);
    addPygmentsLikeMarks(code);
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
                const formatted = format(rawSource.textContent, 'main.cpp', CLANG_FORMAT_STYLE);
                formattedView = buildFormattedView(formatted);
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
