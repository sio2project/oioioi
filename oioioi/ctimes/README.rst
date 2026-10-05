A module implementing an interface for delivering round start
and end times encoded as JSON. Used for locking contestants' computers
before or after a round with oi-timer.

The logic for choosing the round to return info about is as follows:
1. Discard rounds that ended more than 5 minutes ago.
2. Of ongoing rounds, return the one ending first.
3. Of rounds starting in the next 5 minutes, return the earliest starting one.
4. Of recently ended rounds, return the one that ended last.
5. Of future rounds, return the earliest starting one.
