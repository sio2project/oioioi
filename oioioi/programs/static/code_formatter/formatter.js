import init, { format, version } from "./clang-format.js";

// clang-format
async function cpp_code_formatter(source) {
    await init();
    console.log(version());
    const formatted = format(
        source,
        "main.cc",
        JSON.stringify({
            BasedOnStyle: "Chromium",
            IndentWidth: 4,
            ColumnLimit: 80,
        })
    );
    return formatted;
}

async function format_cpp_code() {
    const source = document.getElementById("raw_source").textContent;
    const formatted_source = await cpp_code_formatter(source); 
    const visible_source = document.getElementById("visible_source");
    const coloured_source =  Prism.highlight(formatted_source, Prism.languages.cpp, "cpp"); 
    visible_source.innerHTML = coloured_source;

    const button = document.getElementById("format_btn");
    button.classList.remove("btn-outline-secondary");
    button.classList.add("btn-success");
    button.textContent = gettext("Formatted!");
}

globalThis.format_cpp_code = format_cpp_code;