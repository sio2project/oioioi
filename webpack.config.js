const path = require('path');

module.exports = {
  entry: {
    jquery: './oioioi/base/static/js/jquery.js',
    index: './oioioi/base/static/js/index.js',
    datetimepicker: './oioioi/base/static/js/datetimepicker.js',
    portal_tree: './oioioi/portals/static/portals/portal_tree.js',
    timeline: './oioioi/timeline/static/timeline/timeline.js',
  },
  output: {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'dist_webpack'),
    asyncChunks: false,
  },
  externals: {
    jquery: 'jQuery',
  },
  stats: {
    modules: false,
  },
};