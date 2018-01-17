/*console = {
		log : function() {}
	};*/	
var isDefined = function(obj) {
	return typeof(obj) != "undefined";
};
if (!Math.sign) {
	Math.sign = function(v) {
		if (v < 0) return -1;
		if (v > 0) return 1;
		return 0;
		
	};
}
var mapObjectOwnProperties = function(obj, fun) {
	var k, v, res = {};
	for (k in obj) {
		if (obj.hasOwnProperty(k)) {
			res[k] = fun(obj[k], k, obj);
		}
	}
	return res;
};