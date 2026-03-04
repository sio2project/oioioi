const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
  entry: {
    jquery: './oioioi/base/static/js/jquery.js',
    index: './oioioi/base/static/js/index.js',
    datetimepicker: './oioioi/base/static/js/datetimepicker.js',
    portal_tree: './oioioi/portals/static/portals/portal_tree.js',
    timeline: './oioioi/timeline/static/timeline/timeline.js',
    darkreader: './oioioi/base/static/js/darkreader.js',
  },
  output: {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'dist_webpack'),
    asyncChunks: false,
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        {
          from: 'node_modules/mathjax',
          to: 'mathjax',
          info: { minimized: true },
        },
      ],
    }),
  ],
  externals: {
    jquery: 'jQuery',
  },
  stats: {
    modules: false,
  },
};