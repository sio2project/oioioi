const path = require('path');

module.exports = {
  entry: {
    jquery: './oioioi/base/static/js/jquery.js',
    index: './oioioi/base/static/js/index.js',
    timeline: './oioioi/timeline/static/timeline/timeline.js',
    portal_tree: './oioioi/portals/static/portals/portal_tree.js',
  },
  output: {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'dist_webpack'),
  },
  externals: {
    jquery: 'jQuery',
    moment: 'moment'
  },
};