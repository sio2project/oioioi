===========
Mixins
===========

Dynamic mixins
--------------

.. currentmodule:: oioioi.base.utils

.. autoclass:: oioioi.base.utils.ObjectWithMixins
   :members:


Baseclasses that allow for adding mixins
----------------------------------------

:class:`oioioi.contests.controllers.ContestController`

:class:`oioioi.problems.controllers.ProblemController`

:class:`oioioi.rankings.controllers.RankingController`

:class:`oioioi.contests.controllers.RegistrationController`

:class:`oioioi.base.admin.ModelAdmin`

:class:`oioioi.base.admin.OioioiUserAdmin`

:class:`oioioi.contestexcl.middleware.ExclusiveContestsMiddleware`

:class:`oioioi.problems.package.ProblemPackageBackend`


Admin panel mixins
------------------

.. autoclass:: oioioi.complaints.admin.ComplaintsAdminMixin

.. autoclass:: oioioi.balloons.admin.BalloonsDeliveryAccessDataAdminMixin

.. autoclass:: oioioi.contestexcl.admin.ContestAdminWithExclusivenessInlineMixin

.. autoclass:: oioioi.contestlogo.admin.ContestLogoAdminMixin

.. autoclass:: oioioi.contestlogo.admin.ContestIconAdminMixin

.. autoclass:: oioioi.ipauthsync.admin.ContestAdminWithIpAuthSyncInlineMixin

.. autoclass:: oioioi.mailsubmit.admin.MailSubmissionConfigAdminMixin

.. autoclass:: oioioi.oisubmit.admin.OISubmitSubmissionAdminMixin

.. autoclass:: oioioi.pa.admin.PAProblemInstanceAdminMixin

.. autoclass:: oioioi.participants.admin.OnsiteSubmissionAdminMixin

.. autoclass:: oioioi.participants.admin.UserWithParticipantsAdminMixin

.. autoclass:: oioioi.participants.admin.ParticipantsRoundTimeExtensionMixin

.. autoclass:: oioioi.problems.admin.StatementConfigAdminMixin

.. autoclass:: oioioi.programs.admin.LibraryProblemDataAdminMixin

.. autoclass:: oioioi.programs.admin.ProgrammingProblemAdminMixin

.. autoclass:: oioioi.programs.admin.ProgrammingProblemInstanceAdminMixin

.. autoclass:: oioioi.programs.admin.ProgrammingMainProblemInstanceAdminMixin

.. autoclass:: oioioi.programs.admin.ProblemPackageAdminMixin

.. autoclass:: oioioi.programs.admin.ModelSubmissionAdminMixin

.. autoclass:: oioioi.programs.admin.ProgramSubmissionAdminMixin

.. autoclass:: oioioi.questions.admin.MessageNotifierContestAdminMixin

.. autoclass:: oioioi.scoresreveal.admin.ScoresRevealProgrammingProblemAdminMixin

.. autoclass:: oioioi.scoresreveal.admin.ScoresRevealSubmissionAdminMixin

.. autoclass:: oioioi.sinolpack.admin.SinolpackProblemAdminMixin

.. autoclass:: oioioi.statistics.admin.StatisticsAdminMixin

.. autoclass:: oioioi.suspendjudge.admin.SuspendJudgeProblemInstanceAdminMixin

.. autoclass:: oioioi.teachers.admin.ContestAdminMixin

.. autoclass:: oioioi.teams.admin.TeamsAdminMixin

.. autoclass:: oioioi.testrun.admin.TestRunProgrammingProblemAdminMixin

.. autoclass:: oioioi.testspackages.admin.TestsPackageAdminMixin

.. autoclass:: oioioi.zeus.admin.ZeusProblemAdminMixin


Miscellaneous
-------------

.. autoclass:: oioioi.acm.controllers.NotificationsMixinForACMContestController

.. autoclass:: oioioi.balloons.controllers.BalloonsDeliveryACMControllerMixin

.. autoclass:: oioioi.confirmations.controllers.ConfirmationContestControllerMixin

.. autoclass:: oioioi.contestlogo.controllers.LogoContestControllerMixin

.. autoclass:: oioioi.contests.controllers.NotificationsMixinForContestController

.. autoclass:: oioioi.contests.controllers.PastRoundsHiddenContestControllerMixin

.. autoclass:: oioioi.contests.controllers.ProblemUploadingContestControllerMixin

.. autoclass:: oioioi.dashboard.controllers.DashboardDefaultViewMixin

.. autoclass:: oioioi.disqualification.controllers.DisqualificationContestControllerMixin

.. autoclass:: oioioi.disqualification.controllers.DisqualificationProgrammingContestControllerMixin

.. autoclass:: oioioi.disqualification.controllers.WithDisqualificationRankingControllerMixin

.. autoclass:: oioioi.ipauthsync.controllers.IpAuthSyncControllerMixin

.. autoclass:: oioioi.ipauthsync.controllers.IpAuthSyncRegistrationControllerMixin

.. autoclass:: oioioi.livedata.controllers.LivedataContestControllerMixin

.. autoclass:: oioioi.oisubmit.controllers.OiSubmitContestControllerMixin

.. autoclass:: oioioi.participants.controllers.EmailShowContestControllerMixin

.. autoclass:: oioioi.participants.controllers.AnonymousContestControllerMixin

.. autoclass:: oioioi.participants.controllers.OnsiteContestControllerMixin

.. autoclass:: oioioi.participants.middleware.ExclusiveContestsWithParticipantsMiddlewareMixin

.. autoclass:: oioioi.printing.controllers.PrintingContestControllerMixin

.. autoclass:: oioioi.publicsolutions.controllers.PublicSolutionsContestControllerMixin

.. autoclass:: oioioi.questions.controllers.QuestionsContestControllerMixin

.. autoclass:: oioioi.rankings.controllers.RankingMixinForContestController

.. autoclass:: oioioi.scoresreveal.controllers.ScoresRevealProblemControllerMixin

.. autoclass:: oioioi.scoresreveal.controllers.ScoresRevealContestControllerMixin

.. autoclass:: oioioi.similarsubmits.controllers.SimilarityDisqualificationMixin

.. autoclass:: oioioi.statistics.controllers.StatisticsMixinForContestController

.. autoclass:: oioioi.submitservice.controllers.SubmitServiceMixinForProgrammingContestController

.. autoclass:: oioioi.suspendjudge.controllers.SuspendJudgeContestControllerMixin

.. autoclass:: oioioi.teams.controllers.TeamsMixinForContestController

.. autoclass:: oioioi.testrun.controllers.TestRunProblemControllerMixin

.. autoclass:: oioioi.testrun.controllers.TestRunContestControllerMixin
