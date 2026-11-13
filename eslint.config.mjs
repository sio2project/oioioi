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
  {
    // As per the ESLint docs: Each config file exports an array of config objects.
    // The objects in the array are evaluated in order: later objects may override 
    // settings specified in earlier objects.
    
    files: ["oioioi/**/*.js"],
    ignores: [
      // keep the existing ignores here too — otherwise this block re-enables liveranking etc.
      "**/*.min.js", "oioioi/liveranking/**", "oioioi/notifications/server/**",
      // webpack-bundled ES modules
      "oioioi/base/static/js/**",
      "oioioi/portals/static/portals/portal_tree.js",
      "oioioi/timeline/static/timeline/timeline.js",
    ],
    languageOptions: { sourceType: "script" },
    rules: {
      "no-unused-vars": ["error", { vars: "local", args: "none", caughtErrors: "none" }],
    },
  }
]);