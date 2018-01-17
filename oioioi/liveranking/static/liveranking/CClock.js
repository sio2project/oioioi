var CClock = function(model, targetDiv) {
	var timer = null;
	this.init = function() {
		var that = this;
		$(targetDiv).addClass('pluginClock');
		timer = setInterval(function() {
			var time = model.getTime();
			if (time < 0) {
				$(targetDiv).text(time);
			} else {
				$(targetDiv).text(that.settings.parseTime(time));
			}
		}, 70);
	};
	this.stop = function() {
		clearTimeout(timer);
	};
	
};

CClock.prototype.settings = {	
	'parseTime' : function(time) {
		var s,m,h;
		h = Math.floor(time / 3600);
		m = Math.floor(time % 3600 / 60);
		s = Math.floor(time % 60);
		if (m < 10) m = '0' + m;
		if (s < 10) s = '0' + s;
		return h + ':' + m + ':' + s;
	}
};