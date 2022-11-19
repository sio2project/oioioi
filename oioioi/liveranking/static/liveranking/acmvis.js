var classSimpleInit = function() {		
	var res = function(obj) {
		var l1;		
		for (l1 = 0; l1 < this.fields.length; l1++) {
			this[this.fields[l1]] = obj[this.fields[l1]];
		}
	};
	return res;
};

/*    CTmpEvent
 *    judgingTS - moment ocenienia
 *  submissionTS - moment wysłania
 *  result - status sprawdzania (String)
 *     sumbitId
 *    reportId 
 *     teamId
 *     taskId
 */
var CTmpEvent = function (obj) {
	"use strict";				
    this.simpleInit.call(this, obj);			            
};
CTmpEvent.prototype.fields = [        
	"id",
	"judgingTS",
	"submissionTS",
	"taskId",
	"teamId",
	"result"
];
CTmpEvent.prototype.simpleInit = classSimpleInit(CTmpEvent.prototype.fields);	

/*    CEvent
 *    time - ilosc sekund ktore uplynely od poczatku konkursu do zarejestrowania zgloszenia
 *  result - status sprawdzania ["AC","WA","TL","RE","CE","OT"]
 *     teamId
 *     taskId
 */
CTmpEvent.prototype.isEqual = function(obj) {
	var l1;
	for (l1 = 0; l1 < this.fields.length; l1++) {
		if (this[this.fields[l1]] !== obj[this.fields[l1]]) {
			return false;                
		}
	}
	return true;
};


var CEvent = function (obj) {
	"use strict";				
    this.simpleInit.call(this, obj);		
	if (!CAcmvis.settings.statesMap[this.result]) {	
		console.log('Nieznany status(result) zdarzenia: ' + this.result);
		this.failure = true;
	} else {
		this.result = CAcmvis.settings.statesMap[this.result];	
		this.failure = false;
	}	
	this.copy = function() {
		var res = {}, l1, v;
		for (l1 = 0; l1 < this.fields.length; l1++) {
			v = this.fields[l1];
			res[v] = this[v];
		}
		//console.log(this.fields);
		//console.log(res);
		return res;
	};
};
CEvent.prototype.fields = [        
	"id",
	"time",
	"result",
	"teamId",
	"taskId"        
];
CEvent.prototype.simpleInit = classSimpleInit(CEvent.prototype.fields);	

// stos, uniemożliwia dodanie dwa razy obiektu przeslanego z tym samym id
// obiekty ukladane na stosie musza miec metodę isEqual (służy do wykrywania rejudge)
var CUniquesQueue = function() {
    var stack = [];
    var ids = {};
    
    this.push = function(obj, id) {
        if (!!ids[id]) {
            if (!ids[id].obj.isEqual(obj)) {
                //console.log(obj, ids[id].obj);
                return "REJUDGE";
            }
            return false;
        }
        ids[id] = {"obj" : obj};
        stack.push({
            'obj' : obj,
            'id' : id
        });
        return true;
    };
    
    this.pop = function() {
        var res = stack.pop();
        if (typeof(res) !== "undefined") {
            ids[res.id] = false;
            return res.obj;
        } else {
            return res;
        }
    };
    
    this.isEmpty = function() {
        return stack.length === 0;
    };
};

/*    WYMAGA JQuery
 *    Aby rozpocząć przetwarzanie zgłoszen musi otrzymać sekwencję sterującą z godziną 
 *     rozpoczęcia zawodów, wczesniej zgloszenia gromadzą się w kolejce
 *  startTS jest równy 0 jeśli nie otrzymaliśmy jeszcze timestampu rozpoczęcia zawodów
 *  teams : tablica z id drużyn
 *  tasks : tablica z id zadań
 *
 */
var CAdapter = function(teamsIds, tasksIds) {
    this.rejudge = false;         // czy wystapil rejudge
    this.startTS = 0;           // timestamp rozpoczecia zawodow : [Number, null], null jesli 
                                // nie otrzymalismy jeszcze sekwencji rozpoczynajacej
    this.lastJudgingTS = 0;
	
    this.submits = {};             // mapa CEvents indeksowana kluczami submitId
    
    this.submitsQueue = new CUniquesQueue();        // kolejka CTmpEvents - pobranych ale jeszcze 
                                                    // nieprzetworzonych(niedodanych do this.submits) zgłoszeń    
    
	// minTS, maxTS - odnosi sie do jusgingTimestamp, przedział domkniety
    this.getEvents = function(minTS) { 
        var that = this;		
        if (!minTS) minTS = 0; // jest ok, bo 0 jest zamieniane na 0
        $.ajax({
            url: CAcmvis.settings.eventsSenderUrl,
            async: !!CAcmvis.settings.downloadEventsAsync,        
            dataType: 'json',        
            data: "from=" + Math.max(0, (minTS - 1)),
            success: function(data) { 
                var datum = null;
                for (var l1 = 0; l1<data.length; l1++) {                    
                    datum = data[l1];
                    if (datum.result === "CTRL") {             // jezeli otrzymalismy sekwencje sterujaca
                        if (datum.reportId === "START") {     // jezeli otrzymano sekwencje z timestampem startu zawodów
                            that.startTS = Number(datum.judgingTimestamp);
                        }
                    } else {						
                        that.submitsQueue.push(new CTmpEvent({
                            "id" : datum.submissionId,
                            "judgingTS" : Number(datum.judgingTimestamp),
                            "submissionTS" : Number(datum.submissionTimestamp),
                            "taskId" : datum.taskId,
                            "teamId" : datum.teamId,
                            "result" : datum.result
                        }), datum.submissionId);
						that.lastJudgingTS = Math.max(that.lastJudgingTS, Number(datum.judgingTimestamp));
						//console.log(that.lastJudgingTS, Number(datum.judgingTimestamp));
                    }
                }
                if (!!that.startTS) that.processQueue();
            },
            error: function() { console.log("CAdapter: Nie udało się pobieranie zdarzen"); }
        });                
    };
    
    this.processQueue = function() {
        var rejudge = false; // flaga
        var obj, tmpEvent;
        while (!this.submitsQueue.isEmpty()) {
            obj = this.submitsQueue.pop();
            /*obj = new CEvent({
                "id" : obj.id,
                "time" : obj.submissionTS - this.startTS,
                "result" : obj.result,
                "teamId" : obj.teamId,
                "taskId" : obj.taskId
            });*/
            //if (this.submits.hasOwnProperty(obj.id)) console.log(obj.id, obj, this.submits.hasOwnProperty(obj.id));
            //console.log(obj.id);
            if (this.submits.hasOwnProperty(obj.id) && !obj.isEqual(this.submits[obj.id])) {                
				if (this.submits[obj.id].judgingTS < obj.judgingTS) {
					console.log("REJUDGE");
					this.submits[obj.id] = obj;
				}
            } else {
				tmpEvent = new CEvent({
					"id" : obj.id,
					"time" : obj.submissionTS - this.startTS,
					"result" : obj.result,
					"teamId" : obj.teamId,
					"taskId" : obj.taskId
				});				
				if (!tmpEvent.failure) {
					this.submits[obj.id] = tmpEvent;
				} else {
					console.log('failure: ' + JSON.stringify(tmpEvent));
				}
			}            
        }
    };
	
	// zwraca tablice CEvent posortowana po time
	this.getModelsEvents = function(fromContestTime, toContestTime) {					
		var res = [], k, v;		
		for (k in this.submits) if (this.submits.hasOwnProperty(k)) {
			v = this.submits[k];			
			//console.log(v['time'], fromContestTime, v['time'], toContestTime);
			if (
				(typeof(fromContestTime) == "undefined" || v.time >= fromContestTime) && 
				(typeof(toContestTime) == "undefined" || v.time <= toContestTime) 
			) {				
				res.push(v.copy());
			}
		}
		res.sort(function(a,b) {
			return a.time - b.time;
		});
		return res;		
	};
        
};

CAdapter.prototype.settings = {
	'downloadEventsAsync' : true
};




/* POTENCJALNE PROBLEMY
a) nie ma żadnych flag rejudgeu w przychodzących z serwera danych, w tej chwili przyjmuję, że jeśli pojawią się 
kilka razy submity o tym samym submissionId to aktualny jest ten który ma najwyższy judgingTimestamp 
UWAGA! to może spowodować problem jeśli będzie miał miejsce rejudge w tej samej sekundzie co sprawdzenie jakiegoś 
zgłoszenia, i pojawią się dwa zgłoszenia o tych samych submissionId i judgingTimestamp, ale różnych wynikach sprawdzania
b) czy freezeTime ma być ostry czy nieostry, zakładam, że ostry, jeśli inczaej to należy zamienić w CModel.getEvents:
	to = this.settings.freezeTime - 1;
na 
	to = this.settings.freezeTime;
*/
