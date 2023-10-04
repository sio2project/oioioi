var CRanking = function(model, targetDiv) {	
	// flaga opisujaca czy ranking sie przewija w danym momencie
	this.scrolling = false;
	// mapa teamId -> element jQuery zawierający wiersz odpowiadający danemu zespołowi
	this.teamsDOM = {};
	// mapa taskId -> tablicca elementów jQuery zawierająca elementy odpowiadające danemu zadaniu
	this.tasksDOM = {};
	// mapa map teamId,taskId -> element jQuery
	this.teamToTaskDOM = {};
	this.tasks = [];
	this.targetDiv = targetDiv;
	
	// pelna szerokosc wszystkich komorek, ranking musi byc zaincjalizowany
	var fullWidth;
	this.fullWidth = function() {
		if (isDefined(fullWidth)) {
			return fullWidth;
		}
		return this.settings.taskColWidth * this.tasks.length + this.settings.teamsColWidth + 
			this.settings.scoreColWidth + this.settings.timeColWidth + this.settings.rankColWidth;	
	};
	
	this.addHeaders = function() {
		var name, score, time, pomObj, l1, v, left;		
		var domElem = $('<div />')
			.addClass('headerRow')
			.addClass('static')
			.css({
				'z-index' : this.settings.maxZIndex,
				'height' : this.settings.headerRowHeight + 'px',
				'width' : this.fullWidth()
			});		
		left = 0;
		name = $('<span />')
			.text(this.settings.headerText(0))
			//.css('width', CRanking.settings.rankColWidth + 'px')
			.css('left', left + 'px')
			.addClass('rank')
			.addClass('header')
			.appendTo(domElem);					
		left += this.settings.rankColWidth;
		name = $('<span />')
			.text(this.settings.headerText(1))
			//.css('width', this.settings.teamsColWidth + 'px')
			.css('left', left + 'px')
			.addClass('header')
			.addClass('name')
			.appendTo(domElem);					
		left += this.settings.teamsColWidth;
		score = $('<span />')			
			.text(this.settings.headerText(2))
			.addClass('score')
			.addClass('header')
			//.css('width', this.settings.scoreColWidth + 'px')
			.css('left', left + 'px')			
			.appendTo(domElem);		
		left += this.settings.scoreColWidth;
		time = $('<span />')			
			.text(this.settings.headerText(3))
			//.css('width', this.settings.timeColWidth + 'px')
			.css('left', left + 'px')			
			.addClass('time')
			.addClass('header')
			.appendTo(domElem);			
		left += this.settings.timeColWidth;
		for(l1 = 0; l1 < this.tasks.length; l1++) {			
			v = this.tasks[l1];
			pomObj = $('<span />')				
				.css('left', left + 'px')
				.addClass('header')
				.addClass('task')
				//.css('width', this.settings.taskColWidth + 'px')
				.text(this.settings.headerText(4+l1, v));						
			pomObj.appendTo(domElem);
			this.tasksDOM[v.id].push(pomObj);			
			left += this.settings.taskColWidth;
		}		
		$(domElem).appendTo(this.targetDiv);				
	};
	
	// dodajemy zespół tylko wtedy jeśli nie dodaliśmy go wcześniej	
	this.addTeam = function(team) {
		var name, score, time, pomObj, l1, v, left, domElem;		
		if (!!this.teamsDOM[team.id]) {
			// Zespół został już dodany
			return false;			
		}
		domElem = $('<div />')
			.addClass('row')
			.css({				
				'height' : this.settings.teamRowHeight + 'px',
				'width' : this.fullWidth()
			});
		this.teamToTaskDOM[team.id] = {};
		left = 0;
		name = $('<span />')
			.text('')
			//.css('width', this.settings.rankColWidth + 'px')
			.css('left', left + 'px')
			.addClass('rank')
			.appendTo(domElem);					
		left += this.settings.rankColWidth;
		name = $('<span />')
			.text(this.settings.genTeamName(team))
			//.css('width', this.settings.teamsColWidth + 'px')
			.css('left', left + 'px')
			.addClass('name')
			.appendTo(domElem);					
		left += this.settings.teamsColWidth;
		score = $('<span />')			
			.addClass('score')
			//.css('width', this.settings.scoreColWidth + 'px')
			.css('left', left + 'px')			
			.appendTo(domElem);		
		left += this.settings.scoreColWidth;
		time = $('<span />')			
			.text('00:00:00')
			//.css('width', this.settings.timeColWidth + 'px')
			.css('left', left + 'px')			
			.addClass('time')
			.appendTo(domElem);
		for(l1 = 0; l1 < this.tasks.length; l1++) {
			//console.log('!!!');
			v = this.tasks[l1];
			pomObj = $('<span />')
				.addClass('teamToTask')				
				.text('X');
			this.tasksDOM[v.id].push(pomObj);			
			this.teamToTaskDOM[team.id][v.id] = pomObj;
			pomObj.appendTo(domElem);
		}		
		$(domElem).appendTo(this.targetDiv);				
		this.teamsDOM[team.id] = domElem;		
		return true;
	};
	
	// zwraca mapę teamId->akutalna pozycja(int); numeracja od 0
	this.sortedTeams = function(teams) {
		var array = [], l1, v, res = {};
		for (l1 = 0; l1 < teams.length; l1++) {
			v = teams[l1];
			array.push({
				'id' : v.id, 
				'score' : v.score,
				'time' : v.time
			});
		}		
		array.sort(function(a, b) {
			if (a.score > b.score) return -1;
			if (a.score < b.score) return 1;
			if (a.time < b.time) return -1;
			if (a.time > b.time) return 1;
			if (a.id < b.id) return -1;
			return 1;
		});
		for (l1 = 0; l1 < array.length; l1++) {
			v = array[l1];
			res[v.id] = l1;
		}
		return res;
	};
	
	// zwraca mapę taskId->akutalna pozycja(int); numeracja od 0; sortowane po trudnosci - wiecej AC = wyzej
	this.sortedTasks = function(tasks) {
		var array = [], l1, v, res = {};
		for (l1 = 0; l1 < tasks.length; l1++) {
			v = tasks[l1];
			array.push({
				'id' : v.id, 
				'score' : v.score,
				'shortName' : v.shortName				
			});
		}		
		array.sort(function(a, b) {
			if (a.score > b.score) return -1;
			if (a.score < b.score) return 1;			
			if (a.shortName < b.shortName) return -1;
			return 1;
		});
		for (l1 = 0; l1 < array.length; l1++) {
			v = array[l1];
			res[v.id] = l1;
		}
		return res;
	};
	
	this.internalUpdate = function() {
		var left;
		var l1, rank, k1, k2, teams, team, task, teamTask, sortedTeams, v, modelTime;
		console.log('! ' + !!this.scrolling, this);
		if (!!this.scrolling) {
			console.log('stopped');
			return;
		}
		teams = model.teams.getTeams();	
		if (this.settings.useModelTime) {
			modelTime = model.getTime();
		} else {
			modelTime = model.lastSumissionPassedTime;
		}
		for (l1 = 0; l1 < teams.length; l1++) {
			team =  teams[l1];									
			this.teamsDOM[team.id].find('.score').text(team.score);
			this.teamsDOM[team.id].find('.time').text(this.settings.parseTime(team.time));			
			for (l2 = 0; l2 < this.tasks.length; l2++) {				
				task = this.tasks[l2];
				teamTask = model.getTeamTask(team.id, task.id);				
				this.teamToTaskDOM[team.id][task.id]
					.text(this.settings.parseTeamTask(teamTask))
					.css('background-color', this.settings.getColor(
						teamTask.lastStatus, 
						modelTime - teamTask.lastSubmissionTime)
					);				
				left += this.settings.taskColWidth;
			}
		}
		// przesuwamy wiersze i uzupelniamy kolumne rank
		sortedTeams = this.sortedTeams(teams);		
		for (l1 = 0; l1 < teams.length; l1++) {
			v = teams[l1];			
			rank = sortedTeams[v.id];	
			this.teamsDOM[v.id].css('z-index', this.settings.maxZIndex - 1 - rank);			
			if (rank < this.settings.staticRowsNo) {
				this.teamsDOM[v.id].addClass('static');
			} else {
				this.teamsDOM[v.id].removeClass('static');
			}			
			if (rank < this.settings.staticRowsNo) {
				$(this.teamsDOM[v.id]).removeClass('staticRow');
			}
			this.teamsDOM[v.id]
				.css('top' , (rank * this.settings.teamRowHeight + this.settings.headerRowHeight) + 'px')
				.removeClass('staticRow');
			this.teamsDOM[v.id]
				.find('.rank')
				.text(rank+1);
		}
		// przesuwamy komorki 
		left = this.settings.teamsColWidth + this.settings.scoreColWidth + this.settings.timeColWidth + 
			this.settings.rankColWidth;
		sortedTasks = this.sortedTasks(this.tasks);
		for (l1 = 0; l1 < this.tasks.length; l1++) {
			v = this.tasks[l1];			
			rank = sortedTasks[v.id];						
			for (l2 = 0; l2 < this.tasksDOM[v.id].length; l2++) {
				this.tasksDOM[v.id][l2]
					.css('left' , (rank * this.settings.taskColWidth + left) + 'px');				
			}
		}		
	};
			
	
	this.update = function() {
		var teams = model.teams.getTeams();		
		var l1, v;		
		for(l1 = 0; l1< teams.length; l1++) {
			v = teams[l1];
			this.addTeam(v);
		}		
		console.log('update');
		this.internalUpdate();
	};
	
	// przewijanie listy zespolow, to trzeba przepisac eventy do wykrywania konca tranzycji byly zbyt chimeryczne, 
	// żeby ich używać i jest obrzydliwie
	this.scrollTeams = function(callback) {
		var that = this;
		var non0TeamsNo = 0;		
		this.isAnimated = true;	
		mapObjectOwnProperties(this.teamsDOM, function(v, k) {
			//console.log(k, v, model.teams.getTeam(k));
			// sprawdzamy czy team cos wyslal, mozna sie kiedys zastanowic czy jest sens wprowadzania 
			// szalonego sortowania(WA lepsze niz brak submita)
			/* var hasSubmited = false;
			mapObjectOwnProperties(model.teams.getTeam(k).statesDist.distribution, function(v, k) {
				hasSubmited = hasSubmited || !!v;
			});*/
			if (model.teams.getTeam(k).score > 0) {
				non0TeamsNo++;			
			}
		});		
		//console.log('AAA' + non0TeamsNo);
		
		var step = function(stepsLeft, totalSteps) {			
			var animatedRows = $(that.targetDiv).find('.row:not(.static)');
			that.scrolling = true;
			if (!isDefined(totalSteps)) {
				return step(stepsLeft, stepsLeft);
			}
			if (stepsLeft <= 0) {		
				//console.log(' ----> ' + animatedRows.length, typeof(callback));
				if (animatedRows.length > 0) {					
					/*animatedRows
						.first()
						.bind("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd", function() { 
							$(this).unbind("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd");
							that.scrolling = false;
							console.log(' -> ' + typeof(callback));
							if (typeof(callback) == "function") {
								callback();
							}
						});
					animatedRows.css('margin-top', '-10px');									
					//animatedRows.css('color', '-10px');									
					//animatedRows.css('margin-top', '0px');									
					*/
					animatedRows.css('margin-top', '0px');									
					if (typeof(callback) == "function") {
						that.scrolling = false;
						setTimeout(callback, 3000);
					}
				} else {
					that.scrolling = false;
					//console.log(' -!-> ' + typeof(callback));
					if (typeof(callback) == "function") {
						callback();
					}
				}
				return;
			}
			$(that.targetDiv).find('.row:not(.static)').css(
				'margin-top', 
				'-' + that.settings.teamRowHeight * 6 * (totalSteps - stepsLeft + 1) + 'px'
			);
			setTimeout(function() {
				step(stepsLeft - 1, totalSteps);
			}, 8000);
		};		
		step(
			Math.ceil((non0TeamsNo - this.settings.visibleTeams) / 6)
		);
	};
	
// przewijanie listy zespolow, przepisane na jQuery 
	this.scrollTeams2 = function(callback) {
		var settings = {'delayAfter' : 3000};
		var that = this;
		var non0TeamsNo = 0;		
		var animatedRows = $(that.targetDiv).find('.row:not(.static)');				
		this.isAnimated = true;	
		mapObjectOwnProperties(this.teamsDOM, function(v, k) {			
			if (model.teams.getTeam(k).score > 0) {
				non0TeamsNo++;			
			}
		});		
		//console.log('AAA' + non0TeamsNo);				
		if (typeof(callback) !== "function") {
			callback = null;
		}
		animatedRows.css({'margin-top' : '0px'});
		that.scrolling = true;
		
		var step = function(stepsLeft) {		
			var animatedNo = animatedRows.length;
			//console.log('step :', stepsLeft);			
			if (stepsLeft <= 0) {					
				animatedRows.delay(settings.delayAfter).animate(
					{'margin-top' : '0px'},
					800,
					function() {
						if (!!(--animatedNo)) return;						
						that.scrolling = false;
						if (!!callback)  callback();
					}					
				);																		
			} else {
				//window.animRows = animatedRows;
				//console.log(stepsLeft, animatedRows);
				$(animatedRows).animate(
					{'margin-top' : '-=' + that.settings.teamRowHeight + 'px'},
					500, 
					function() { 
						//console.log('animatedNo' + animatedNo);
						if (!!(--animatedNo)) return;						
						//console.log('!', stepsLeft);					
						//console.log('animacja zakonczona'); 
						setTimeout(function() {
							step(stepsLeft - 1);
						}, 1500);
					}
				);					
			}			
		};	
				
		if (non0TeamsNo - this.settings.visibleTeams <= 0) {			
			this.scrolling = false;
			if (!!callback) {
				callback();
			}
		} else {
			step(non0TeamsNo - this.settings.visibleTeams);
		}		
	};	
		
	// w momencie zainicjalizowania rankingu model musi byc zainicjalizowany i przechowywac wszystkie zadania 
	// jakie zostaną wykorzystane w trakcie zawodów
	this.init = function() {
		console.log('init');
		var l1, v, fullHeight;		
		
		this.tasks = model.tasks.getTasks();		
		for (l1 = 0; l1 < this.tasks.length; l1++) {
			v = this.tasks[l1];
			//console.log(v);
			this.tasksDOM[v.id] = [];
		}		
		
		this.addHeaders();		
		fullHeight = this.settings.visibleTeams * this.settings.teamRowHeight + this.settings.headerRowHeight;
		$(this.targetDiv)
			.css('height', fullHeight + 'px')
			.addClass('pluginRanking');
		$(this.targetDiv).css('width', this.fullWidth() + 'px');
	};

};

CRanking.prototype.settings = {
	'headerRowHeight' : 50,
	'teamRowHeight' : 40,
	'staticRowsNo' : 4, //liczba nieruchomych wierszy, nie wliczając nagłówka, dotyczy przewijania rankingu	
	'rankColWidth' : 60,
	'teamsColWidth' : 250,
	'scoreColWidth' : 90,
	'taskColWidth' : 50,
	'timeColWidth' : 120,
	'visibleTeams' : 10,
	'useModelTime' : true, 	//jezeli true uzywa model.getTime(), jezeli false to model.lastSumissionPassedTime, 
							// do okreslania wieku zdarzenia i doboru kolorów tła
	'parseTime' : function(time) {
		var s,m,h;
		h = Math.floor(time / 3600);
		m = Math.floor(time % 3600 / 60);
		s = time % 60;
		if (m < 10) m = '0' + m;
		if (s < 10) s = '0' + s;
		return h + ':' + m + ':' + s;
	},
	'genTeamName' : function(team) {
		return team.name;
        // return team.name.match(/[^ ][\wńśćąęółżź]+$/)[0];
	},
	'parseTeamTask' : function(teamTask) {
		if (teamTask.lastStatus == null) return "";
		if (teamTask.lastStatus == 'AC' && teamTask.penalty == 0) return 'AC';
		//return teamTask.lastStatus;
		return teamTask.lastStatus + '(' + teamTask.penalty + ')';
	},
	'headerText' : function(no, task) { //teksty nagłówków, kolumny numerowane od 0
		if (no == 0) return "Rank:";
		if (no == 1) return "Name:";
		if (no == 2) return "Score:";
		if (no == 3) return "Time:";
		return task.shortName;
	},
	'colors' :{
		"AC" : {
			'fresh' : '#59B300',
			'old' : '#336600'
		},
		"WA" : {
			'fresh' : '#B30000',
			'old' : '#660000'
		},
		"TL" : {
			'fresh' : '#0059B3',
			'old' : '#006666'
		},
		"CE" : {
			'fresh' : '#000000',
			'old' : '#000000'
		},
		"RE" : {
			'fresh' : '#666600',
			'old' : '#554400'
		},
		"ML" : {
			'fresh' : '#666600',
			'old' : '#554400'
		},
		"??" : {
			'fresh' : '#FF6633',
			'old' : '#CC3300'
		},
		"default" : {
			'fresh' : '#000000',
			'old' : '#000000'
		}		
	},
	'getColor' : function(status, age) { // age - ilosc sekund jakie uplynely od zgloszenia		
		if (!this.colors[status]) {
			status = 'default';
		}
		if (!this.colors[status].interpolator) {
			this.colors[status].interpolator = d3.interpolateRgb(this.colors[status].fresh, this.colors[status].old);
		}				
		return this.colors[status].interpolator(Math.min(age / 1800, 1));		
	},
	'maxZIndex' : 100000	
};
