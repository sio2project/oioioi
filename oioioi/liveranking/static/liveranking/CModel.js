
var CStatesDistribution = function() {
	this.distribution = {};	
};
// status : string, kod statusu
CStatesDistribution.prototype.addStatus = function(status) {
	if (typeof(this.distribution[status]) == "undefined")
		this.distribution[status] = 0;
	this.distribution[status]++;
};
// status : string, opcjonalny kod statusu 
CStatesDistribution.prototype.get = function(status) {
	if (!status) 
		return this.distribution;
	else
		return this.distribution[status];
};
 
 

 
var CModelTeam = function(obj) {
	"use strict";				
    this.simpleInit.call(this, obj);	
	// uaktualnia dane druzyny
	// delta : {"dScore" : zmiana wyniku, "dPenalty" : zmiana ilości bomb, 
	// "status" : nowy wynik zgłoszenia(wykorzystwany do akutalizacji statesDist, "dTIme" : zmiana czasu}			
	// PRZENIESIONE do CModelTeams
	/*
	this.update = function(delta) {
		this.score += deltadScore;
		this.time += delta.dTime;
		this.statesDist.add(delta.status);			
	}*/
};
CModelTeam.prototype.fields = [        
	"id",
	"name",
	"login",
	"initialPosition",
	"score",
	"time",
	"statesDist"
];
CModelTeam.prototype.simpleInit = classSimpleInit(CModelTeam.prototype.fields);	
CModelTeam.prototype.reset = function() {
	this.time = 0;
	this.statesDist = new CStatesDistribution();
	this.score = 0;
};


var CModelTeams = function() {
	this.teams = {};
	this.addTeam = function(team) {
		this.teams[team.id] = new CModelTeam(team);	
		console.log('dodajemy zespół');
	};
	this.getTeams = function() {
		var res = [], k;
		for (k in this.teams) 
			if (this.teams.hasOwnProperty(k))
				res.push(this.teams[k]);
		return res;
	};
	this.getTeam = function(id) {
		if (!this.teams.hasOwnProperty(id))
			return false;
		else
			return this.teams[id];
	};
	this.hasTeam = function(id) {
		return !!this.getTeam(id);		
	};
	this.reset =function() {
		var k;
		for (k in this.teams) if (this.teams.hasOwnProperty(k)) {
			this.teams[k].reset();
		}
	};
	this.updateTeam = function(id, delta) {		
		if (!!delta.dScore)
			this.teams[id].score += delta.dScore;
		if (!!delta.status)
			this.teams[id].statesDist.addStatus(delta.status);
		if (!!delta.dTime)
			this.teams[id].time += delta.dTime;
	};
};

var CModelTask = function(obj) {
	"use strict";				
    this.simpleInit.call(this, obj);	
};
CModelTask.prototype.fields = [        
	"id",
	"shortName",
	"name",
	"statesDist",
	"score"
];
CModelTask.prototype.simpleInit = classSimpleInit(CModelTask.prototype.fields);	
CModelTask.prototype.reset = function() {	
	this.statesDist = new CStatesDistribution();
	this.score = 0;
};




var CModelTasks = function() {
	this.tasks = {};
	this.addTask = function(task) {
		this.tasks[task.id] = new CModelTask(task);				
	};
	this.getTasks = function() {
		var res = [], k;
		for (k in this.tasks) 
			if (this.tasks.hasOwnProperty(k))
				res.push(this.tasks[k]);
		return res;
	};	
	this.hasTask = function(id) {
		return !!this.tasks[id];		
	};
	this.reset = function() {
		var k;
		for (k in this.tasks) if (this.tasks.hasOwnProperty(k)) {
			this.tasks[k].reset();
		}
	};
	this.updateTask = function(id, delta) {		
		if (!!delta.dScore)
			this.tasks[id].score += delta.dScore;
		if (!!delta.status)
			this.tasks[id].statesDist.addStatus(delta.status);		
	};
	
};

var CModelTeamTask = function() {	
	this.init();
};


CModelTeamTask.prototype.init = function() {
	this.score = 0;
	this.penalty = 0;
	this.time = 0;
	this.lastStatus = null;
	this.lastSubmissionTime = 0;
	this.statesDist = new CStatesDistribution();	
};
CModelTeamTask.prototype.reset = CModelTeamTask.prototype.init;
// funkcja zwraca false jesli zdarzenie bylo ignorowane, w przeciwnym razie zwraca 
// obiekt opisujacy zmiane - CStateDelta
CModelTeamTask.prototype.processEvent = function(event) {
	var dScore, dPenalty, state;
	// ignorujemy zgloszenia jesli drużyna uzyskala już AC na dane zadanie
	if (this.score > 0) {
		return false;
	}	
	dScore = CAcmvis.settings.scores[event.result];
	dPenalty = CAcmvis.settings.penalties[event.result];
	status = event.result;
	this.lastStatus = event.result;
	this.lastSubmissionTime = event.time;
	this.score += dScore;
	this.penalty += dPenalty;
	this.statesDist.addStatus(status);
	if (this.score == 1) {
		this.time = event.time + this.penalty * CAcmvis.settings.bombPenalty;
	}
	return  {
		"dScore" : dScore,
		"dPenalty" : dPenalty, 
		"status" : status,
		"dTime" : this.time
	};
};

var CModel = function(adapter) {
	this.teams = new CModelTeams();
	this.tasks = new CModelTasks();
	this.teamToTask = {};
	this.events = [];		
	this.adapter = adapter;
	this.internalTime = 0;
	this.lastSumissionPassedTime = 0;

	this.processEvent = function(event) {				
		var deltas;
		// odrzucamy zdarzenie jesli zadanie nie istnieje 
		if (!this.tasks.hasTask(event.taskId)) {			
			return;
		}
		// sprawdzamy czy zespół istnieje, jeśli nie dodajemy go
		// dla bezpieczenstwa nie dodajemy teamow w czasie finalo
		if (!this.teams.hasTeam(event.teamId)) {			
			return;
			// this.addTeam({
			// 	"id" : event.teamId,
			// 	"login" : event.teamId,
			// 	"name" : event.teamId,
			// 	"initialScore" : 0,
			// 	"time" : 0,
			// 	"statesDist" : new CStatesDistribution(),
			// 	"score" : 0
			// });
		}		
		// przetwarzamy zdarzenie
		this.lastSumissionPassedTime = Math.max(this.lastSumissionPassedTime, event.time);
		deltas = this.teamToTask[event.teamId][event.taskId].processEvent(event);	
		this.teams.updateTeam(event.teamId, deltas);
		this.tasks.updateTask(event.taskId, deltas);
		/*console.log("------------");
		console.log(JSON.stringify(deltas));
		console.log(JSON.stringify(this.teams.getTeam(event.teamId)));*/
	};
	
	// resetuje stan zawodnikow, zespolow i ich par(teamToTask), wprowadzone ze względu na problemy z obsługą rejudge
	this.reset = function() {
		var k1, k2;
		this.teams.reset();
		this.tasks.reset();
		for (k1 in this.teamToTask) if (this.teamToTask.hasOwnProperty(k1))
			for (k2 in this.teamToTask[k1]) if (this.teamToTask[k1].hasOwnProperty(k2)) {
				this.teamToTask[k1][k2].reset();
			}
	};
	
	// zalozenia: żadne zdarzenie nie zostanie przekazane do modelu więcej niż raz, zdarzenia będą przekazywane 
	// w kolejności, nie tylko w ramach jednego zapytania, ale również między zapytaniami, 
	// kiedy te waruneki zostaną spelnione można wyłączyć flage reset
	this.getEvents = function(from, to, reset) {
		var events, l1, v;
		// wymuszamy reset zeby za kazdym razem przeliczyc zawody od poczatku(problemy z rejudgeami)
		reset = true;
		if (reset) {
			from = 0;
			to = this.internalTime;
			this.reset();
		}
		if (!isDefined(from)) from = 0;		
		if (!isDefined(to)) to = CAcmvis.settings.freezeTime - 1;
		events = this.adapter.getModelsEvents(from, to);
		for (l1 = 0; l1 < events.length; l1++) {
			v = events[l1];
			this.processEvent(v);
		}		
		//console.log(events);
	};
	
	// w momencie dodawania zespółów muszą być już zdefiniowane zadania(this.tasks)
	this.getTeams = function() {
		var that = this;
		$.ajax({
			url: CAcmvis.settings.teamsSenderUrl,
			async: false,
			dataType: 'json',        
			success: function(data) { 
				for (var l1=0; l1<data.length; l1++) 
					that.addTeam({
						"id" : data[l1].id,
						"login" : data[l1].login,
						"name" : data[l1].name,
						"initialScore": data[l1].initialScore,
						"time" : 0,
						"statesDist" : new CStatesDistribution(),
						"score" : data[l1].score
					}); 
			},
			error: function(a,b,c) { 
				alert("Nie udało się pobieranie zespołów"); 
			}
		});    	
	};
	
	this.getTasks = function() {
		var that = this;
		$.ajax({
			url: CAcmvis.settings.tasksSenderUrl,
			async: false,
			dataType: 'json',        
			success: function(data) { 				
				for (var l1=0; l1<data.length; l1++) 
					that.tasks.addTask({
						"id" : data[l1].id,
						"shortName" : data[l1].shortName,
						"name" : data[l1].name,
						"statesDist" : new CStatesDistribution()
					}); 
			},
			error: function(a,b,c) { 
				alert("Nie udało się pobieranie zadań");
			}
		});    	
	};	
	
	this.addTeam = function(team) {
		var v, l1, tasks;
		if (!!this.teams.getTeam(team.id) || team.id == 73749) {
			console.log("Próba dodania już dodanego zespołu");
			return false;
		}
		// dodajemy zespół
		this.teams.addTeam(team); 
		// dodajemy objekt CModelTeamTask dla każdej pary <team, istniejące_zadanie>
		this.teamToTask[team.id] = {};
		tasks = this.tasks.getTasks();
		for (l1 = 0; l1< tasks.length; l1++) {
			v = tasks[l1];
			this.teamToTask[team.id][v.id] = new CModelTeamTask();
		}
		return true;
	};
	this.setTime = function(time) {		
		this.internalTime = Math.max(0, Math.min(CAcmvis.settings.contestLength, time));
	};
	
	this.getTime = function() {
		return this.internalTime;
	};
	
	this.init = function() {
		var k1, k2, teams, tasks;
		// pobieranie zadan musi byc pierwsze, zakładamy, że lista zadań jest znana przed zawodami, 
		// w przypadku zespołów może być inaczej(mogą być dodawane dynamicznie)
		this.getTasks();		
		this.getTeams();		
		tasks = this.tasks.getTasks();
		teams = this.teams.getTeams();					
	};	
	this.getTeamTask = function(teamId, taskId) {
		return this.teamToTask[teamId][taskId];
	};
};




