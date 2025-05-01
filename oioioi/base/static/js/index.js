import "bootstrap"
import "bootstrap-3-typeahead"

//https://github.com/webpack-contrib/expose-loader/issues/188
import 'fix.js!=!expose-loader?exposes=Cookies|default!js-cookie';

import "./utils"
import "./csrf_link_protect"
import "./language-picker"
import "./bootstrap-async-collapsible"
import "./bootstrap-table-responsive-dropdown-fix"
import "./bootstrap-tooltip-setup"
import "./menu-setup"
import "./highlight-setup"
import "./clipboard-setup"