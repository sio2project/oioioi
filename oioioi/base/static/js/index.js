import "bootstrap"
import "bootstrap-3-typeahead"

// https://github.com/webpack-contrib/expose-loader/issues/188
import Cookies from "js-cookie"
window.Cookies = Cookies

import "./utils"
import "./csrf_link_protect"
import "./language-picker"
import "./bootstrap-async-collapsible"
import "./bootstrap-table-responsive-dropdown-fix"
import "./menu"
import "./highlight"
import "./clipboard-setup"

// No idea
$(function () {
    $("[data-toggle='tooltip']").tooltip();
});