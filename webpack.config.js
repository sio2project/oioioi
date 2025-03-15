const path = require('path');

module.exports = {
  entry: {
    jquery: './oioioi/base/static/js/jquery.js',
    index: './oioioi/base/static/js/index.js',
  },
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, 'dist_webpack'),
  },
  externals: {
    jquery: 'jQuery',
  },
};