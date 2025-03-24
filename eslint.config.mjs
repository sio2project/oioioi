import { defineConfig } from "eslint/config";
import globals from "globals";
import js from "@eslint/js";


export default defineConfig([
  {
    files: ["oioioi/**/*.js"],
    ignores: [
      "**/*.min.js",
      "oioioi/liveranking/**",
      "oioioi/notifications/server/**",
    ],
    languageOptions: {
      globals: {
        ...globals.browser,
        $: "readonly",
        jQuery: "readonly",
        Cookies: "readonly",
        Highcharts: "readonly",

        django: "readonly",
        gettext: "readonly",
        ngettext: "readonly",
        interpolate: "readonly",

        oioioi_base_url: "readonly",
      }
    },
    plugins: { js },
    extends: ["js/recommended"]
  },
]);