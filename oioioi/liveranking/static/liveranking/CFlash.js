var CFlash = function(model, targetDiv) {	
	// indeksowana id, zawiera obirkty 
	// { 'score' : score, 'acTasksIds' : {task1Id : true, task2Id : true} }
	this.teams = {};	
	this.targetDiv = targetDiv;
	// zawiera {team: 'team.login' , task: 'task.shortName'}
	this.flashQueue = [];
	var queueHead = 0;
	this.getHead = function() {return queueHead;};
	this.timer = null;
	
	this.addToQueue = function(teamLogin, taskShortName) {
		this.flashQueue.push({
			'team' : teamLogin,
			'task' : taskShortName
		});
	};
	
	this.getFromQueue = function() {
		if (queueHead >= this.flashQueue.length) {
			return null;
		} else {			
			return this.flashQueue[queueHead++];
		}
	};
	this.queueLength = function() {
		return this.flashQueue.length - queueHead;
	};
	
	this.emptyQueue = function() {
		while (!!this.getFromQueue()) {			
		}
	};
	
	// dodajemy zespół tylko wtedy jeśli nie dodaliśmy go wcześniej	
	this.addTeam = function(team) {		
		if (!!this.teams[team.id]) {
			// Zespół został już dodany
			return false;			
		}
		this.teams[team.id] = {
			'score' : 0,
			'acTasksIds' : {}
		};
		return true;
	};
	
	this.addTeamAcs = function(team) {
		//console.log('!!!' + team.login);
		//alert('!');
		var l1, tasks, hasAc, task;
		tasks = model.tasks.getTasks();
		for (l1 = 0; l1 < tasks.length; l1++) {
			task = tasks[l1];
			hasAc = !!model.getTeamTask(team.id, task.id).score;
			if (!this.teams[team.id].acTasksIds[task.id] && hasAc) {
				this.teams[team.id].acTasksIds[task.id] = true;
				this.addToQueue(team.name.match(/[^ ][\wńśćąęółżź]+$/)[0], task.shortName);
			}
		}
	};

	this.addNewAcs = function() {
		var l1, team, teams = model.teams.getTeams();
		for (l1 = 0; l1< teams.length; l1++) {
			this.addTeam(teams[l1]);
		}
		for (l1 = 0; l1< teams.length; l1++) {
			team = teams[l1];
			//console.log(team.login, team.score, this.teams[team.id].score);
			if (team.score > this.teams[team.id].score) {				
				this.addTeamAcs(team);
			}
		}		
	};
	
			
	
	this.update = function() {
		this.addNewAcs();
		console.log(this.flashQueue);
	};
		
	// w momencie zainicjalizowania rankingu model musi byc zainicjalizowany i przechowywac wszystkie zadania 
	// jakie zostaną wykorzystane w trakcie zawodów	
	this.init = function() {
		var that = this;		
		var licznik = this.settings.ticksWhileOnScreen;		
		$(that.targetDiv).addClass('flashPlugin');
		console.log('init');								
		setInterval(function() {
			var qObj;
			console.log("Licznik: " + licznik);
			if (licznik > 0) {
				licznik--;
			} else {
				if (that.queueLength() >= that.settings.emptyQueueOn) {
					that.emptyQueue();
				}
				qObj = that.getFromQueue();
				licznik = that.settings.ticksWhileOnScreen;
				if (!!qObj) {									
					var teamName = qObj.team;
					var taskName = qObj.task;
					$(that.targetDiv)
						.addClass('visible')
						.html(teamName + '<br />' + taskName);
				} else {					
					$(that.targetDiv)
						.removeClass('visible');
				}
			}
		}, this.settings.refreshRate);
	};

};

CFlash.prototype.settings = {	
	'refreshRate': 1000,
	'ticksWhileOnScreen' : 3,
	'emptyQueueOn' : 10 // <- ilosc zdarzen w kolejce przy ktorej po prostu ja oprozniamy(aby uniknac duzej ilosci 
						// flashy w przypadku odswierzenia strony z wizualizacja w trakcie zawodow)
};