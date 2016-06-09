var CDonut = function(model, targetDiv) {		
	var newData, oldData, defaultData;
	var settings = this.settings;
	
	this.statesDistributionToFlatArray = function(dist) {
		var l1, v, res = [], sumIs0 = true;		
		for(l1 = 0; l1 < this.settings.states.length; l1++) {
			v = this.settings.states[l1];
			res.push({
				'name' : v,
				'value' : (!!dist.distribution[v]) ? dist.distribution[v] : 0
			});
			if (!!dist.distribution[v]) {
				sumIs0 = false;
			}
		}
		if (sumIs0) {
			res = defaultData;
		}
		return res;
	};
	
	this.arcGenerator = function (datum) {		
		return d3.svg.arc()			
			.innerRadius(settings.r * .82)
			.outerRadius(settings.r)(datum); 		    
	};
	
	this.arcCalculator = d3.layout.pie()			
		.sort(null)
		.startAngle(-0.5)
		.endAngle(5.2)		
		.value(function(datum) { 
			return datum.value; 
		});
	
	this.init = function() {				
		var svg = d3.select(targetDiv)
			.append("svg")
			.attr("width", this.settings.width)
			.attr("height", this.settings.height)
			.append("g")
			.attr("class", "mainGroup")
			.attr("transform", "translate(" + settings.width / 2 + "," + settings.height / 2 + ")");				
		d3.select(targetDiv)
			.classed("pluginDonut", true)
			.append("div")
			.attr("class", "textBox")
			.style("left", (settings.width / 2) + 'px')
			.style("top", (settings.height / 2) + 'px');			
			
		newData = this.statesDistributionToFlatArray({
			'distribution' : {'??' : 1}
		});
		defaultData = this.statesDistributionToFlatArray({
			'distribution' : {'??' : 1}
		});
	}
	
	this.update = function(ldata, name) {
		var that = this;	
		var pie = this.arcCalculator;
		var g;
		var svg = d3.select(targetDiv).select('g.mainGroup');						
		var data;
		
		data = this.statesDistributionToFlatArray(ldata);
		oldData = newData;
		newData = data;		
		data = [pie(data), pie(oldData)];				
		data = d3.transpose(data);
		
		g = svg.selectAll(".arc")
			.data(data)
			.enter();		
		g.append("g")
			.attr("class", "arc")
			.append("path")
			.attr("d", this.arcGenerator)			
			.attr('stroke', '#C0C0C0')			
			.attr('fill', function(datum) {
				datum = datum[0].data;
				if (!datum.name || !that.settings.colors[datum.name]) {				
					return that.settings.colors['default'];
				} else {
					return that.settings.colors[datum.name];
				}
			})
            .attr('stroke-width', '1px');		
		svg.selectAll(".arc").select('path')			
			.attr('visibility', function(datum) {
				if (datum[0].data.value > 0) {
					return "visible";
				} else {
					return d3.select(this).style('visibility');
				}
			})
			.transition()
            .duration(1500)            
            .attrTween("d", function(datum) {                                 
                return function(t) {                    
                    return that.arcGenerator({
						'startAngle' : (1-t)*datum[1].startAngle+t*datum[0].startAngle,
                        'endAngle' : (1-t)*datum[1].endAngle+t*datum[0].endAngle
					});
                };
            })			
			.attrTween('visibility', function(datum) {				
				var that = this; // <- animowany element DOM 
				return function(t) {
					if(t < 0.99) {					
						return d3.select(that).style('visibility');
					} else {
						if (datum[0].data.value == 0) {
							return "hidden";
						} else {
							return d3.select(that).style('visibility');
						}
					}
				};
			});
		// wpisujemy tekst do elementu w srodku paczka
		d3.select(targetDiv)
			.select(".textBox")
			.html(this.settings.textGenerator(ldata, name));
		
	}
	
	this.stop = function() {
		
	}
	
};

CDonut.prototype.settings = {	
	"width" : 480,
	"height" : 480,
	'r' : 230,
	'states' : [
		"AC",
		"WA",
		"TL",
		"CE",
		"RE",
		"ML",
		"??"
	],
	'colors' :{
		"AC" : '#59B300',
		"WA" : '#B30000',
		"TL" : '#0059B3',
		"CE" : '#000000',
		"RE" : '#666600',
		"ML" : "#9923e7",
		"??" : '#FF6633',
		"default" : '#000000'
	},
	"textGenerator" : function(scoreDistribution, name) {
		var score = 0;		
		if (!!scoreDistribution.distribution['AC']) {
			score = scoreDistribution.distribution['AC'];
		}
		return '<span class="nameRow">' + name + '</span>' +
			'<span class="scoreRow">' + score + '</span>';
	}
};
