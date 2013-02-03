String.prototype.fmt = function(dict) {
    return interpolate(this, dict, true);
}
