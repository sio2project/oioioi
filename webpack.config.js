const path = require('path');

module.exports = {
  entry: './oioioi/base/static/js/vendor.js',
  output: {
    filename: 'vendor.js',
    path: path.resolve(__dirname, 'dist_webpack'),
  }
};