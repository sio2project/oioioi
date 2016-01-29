# WARNING: If you change anything here at all, whole level calculations will go
#          down the toilet, probably Experience.force_recalculate_all() should
#          fix your problems then, generally changing this file while
#          already deployed might make you unhappy

# Before soft cap the level calculations will be done using exponential formula,
# afterwards -> linear
SoftCapLevel = 20

# Experience for level x:
# f(x) = ExpBase ^ (x - 1) * ExpMultiplier
ExpMultiplier = 100
ExpBase = 1.25
# Experience for level x:
# f(x) = f(SoftCapLevel) + (x - SoftCapLevel) * LinearMultiplier
LinearMultiplier = 250

# Constants for awarding experience per each problem submission
# There are 5 levels of difficulty, each giving different experience
Lvl1TaskExp = 35
Lvl2TaskExp = 100
Lvl3TaskExp = 200
Lvl4TaskExp = 700
Lvl5TaskExp = 900

# The experience is thought out in a way that you can't level up doing only easy
# taks, thus we can start suggesting a bit harder tasks on some level, thus
# controlling user progress, constants below control at which level we suggest
# what tasks
SuggestLvl2From = 5
SuggestLvl3From = 10
SuggestLvl4From = 15
SuggestLvl5From = 18

# Set this to false if you want to roll your own CodeSharingController
CODE_SHARING_FRIENDS_ENABLED = True
CODE_SHARING_PREFERENCES_DEFAULT = True
