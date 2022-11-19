var CPanel = function(model, plugin) {
	// mnoznik - zmiana czasu rzeczywistego do zmiana czasu w playbacku
	var speed = 20.0;		
	var timerClock = null;
	
	this.next = function() {
		var time = model.getTime() + 1800;
		model.setTime(time);
		model.getEvents(); 
		plugin.update();
	};
	
	this.prev = function() {
		var time = model.getTime() - 1800;
		model.setTime(time);
		model.getEvents(); 
		plugin.update();
	};
	
	this.incSpeed = function() {
		if (speed == -1 || speed == 0) {
			speed += 1;
		} else {
			speed = Math.round(speed * Math.pow(2, Math.sign(speed)));
		}
	};
	
	this.decSpeed = function() {				
		if (speed == 1 || speed == 0) {
			speed -= 1;
		} else {
			speed = Math.round(speed * Math.pow(0.5, Math.sign(speed)));
		}
	};
	
	this.init = function(fun) {
		var freq = 50;				
		setInterval(function() {
			var time = model.getTime();
			model.setTime(time + speed);
			model.getEvents(); 
			if (!!fun) fun();
		}, 1000);
	};
};		