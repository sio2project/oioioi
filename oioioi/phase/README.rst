This module implements phases.

A basic use case for them is:
 - contestants during the contest get a x1.0 score multiplier
 - afterwards (when they get editorials) they get x0.75
 - after 21:00 they get x0.6, so they go to sleep (at least that's the intention)

The formula is roughly as follows:
    new_result = previous_result + (new_result - previous_result) * new_phase
The result from a given phase is the last one to compile correctly.

Currently, no results get updated when somebody changes the phases.
Use the update_scores management command for that.

To enable this feature, use oioioi.phase.controllers.PhaseMixinForContestController.
