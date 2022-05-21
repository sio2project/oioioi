=====================
Developing guidelines
=====================


How to Create a Change
----------------------

1. A programmer fixes his imagination in a tangible form called a hack.
    Let's say you have found some bug in our code you think you can fix, or picked up some nice ticket on our JIRA issues list.
    In other words, you want to make a change in SIO2. If you haven't contributed to any open source project before,
    you may find yourself a bit confused. This tutorial will help you get started in developing SIO2.
2. The programmer gets some pizza, enters the cleanroom and hacks.
    Hacking should be started from a clean and up-to-date repository state, for example by creating
    a new branch from *origin/master*.::

        $ git fetch
        $ git checkout -b my_new_hack origin/master

    Then the programmer hacks until he thinks the hack is good enough that no reviewer will
    think that this is a hack, but everyone will see the beauty of a clean solution.
3. The programmer writes tests for the code.

4. The programmer sends his change for review.
    The programmer should commit the change locally, adding a meaningful description,
    not forgetting to place the ID of the Jira issue, if any.::

        $ git add ...
        $ git rm ...
        $ git commit

    If there is a ticket no XXX connected with the commit the commit message should look like: ::

        SIO-XXX The name of ticket

        description

    Otherwise you should start your message with (no-ticket).

    Then the change should be admired by its author. After going into admiration of his own change,
    the programmer wants others to admire it as well. Artists use galleries for this, programmers use Gerrit_.

    .. _Gerrit: https://gerrit.sio2project.mimuw.edu.pl/

    The process looks like this:
    - the programmer sends the change using
    ``$ git push origin HEAD:refs/for/master``
    This sends all the local commits which are not in origin/master to Gerrit.
    Each commit creates a separate Gerrit change.
    - the programmer may open each of the created Gerrit changes to assign specific
    reviewers through the web interface.
    The programmer may add reviewers manually or wait for someone from the SIO2 team to assign them.

    After the changes are uploaded to Gerrit, the tests will be automatically run for each of them.
    If any of the tests fail, the change bust be fixed (see the next section).

    In order to submit the change to the main repository, the change must meet the requirements listed below.
    - a *Verification OK* status from our automatic tester — Hudson
    - *Looks Good To Me* from all assigned reviewers

5. The programmer sees a review.
    If the programmer disagrees with reviewer's comments, they should discuss the issue on Gerrit
    (using Review with no score) or in person, on Jabber, by e-mail, etc.
    If there are problems with going into agreement, write to *sio2@sio2project.mimuw.edu.pl*.

    Often the Gerrit change needs to be updated. This is done by uploading additional *patch sets*.
    You do this by "changing" the Git commit in your local repository,
    but retaining the original Change-Id: line, which is added automatically to all Git commit messages.

    So for example, assuming that your branch was named *my_new_hack*, you should do something like this:
    ::

        $ git fetch
        $ git checkout my_new_hack
        $ git rebase origin/master
        $ # some hacking
        $ git add ...
        $ git rm ...
        $ git commit --amend
        $ git push origin HEAD:refs/for/master

    Please do not change the *Change-Id* line in the change description.
    If there is no *Change-Id* line, make sure that appropriate Git hooks are installed.

    After this, the change in Gerrit should show a new patch set, which again should be reviewed by the reviewer.
    Automatic e-mail message is sent to all reviewers as well.

    If you don't have your branch, or don't know which one is that one, copy the command directly from Gerrit.
    It should look like:
    ::

        $ git fetch ssh://_YOUR_LOGIN_@ripper.dasie.mimuw.edu.pl:29418/sio2 refs/changes/52/552/2 && git checkout FETCH_HEAD

6. The programmer wants his change submitted to the repository.
    There are two cases here:
    - the developer is a distinguished contributor and belongs to the *sio2-developers*
    group in our accounts system, it's his job to click *Submit Patch Set #* in Gerrit.
    - Otherwise the last reviewer who adds *Looks Good to Me* should attempt to submit.

    If Gerrit says "Cannot merge due to conflicts", this means that some conflicting changes were accepted
    while the change was under review.
    **The author** must rebase the change to the current *origin/master*, resolving eventual conflicts.
    ::

        $ git fetch
        $ git checkout my_new_hack
        $ git rebase origin/master
        $ git push origin HEAD:refs/for/master

    While rebasing, you may have to manually resolve some conflicts.
    Type git status to check the files causing conflicts. After resolving them, type ``git rebase --continue``.
    After the change is submitted, if there is a Jira issue for the change, the programmer *resolves* the Jira issue.
    The programmer may resolve the Jira issue directly from Gerrit, by adding a review comment with ``#RESOLVE`` string in it.
    Please do it only after the issue is submitted to the main repository.
    The programmer may now delete the local Git branch.


How to Do a Review
------------------

Reviewers assigned by the change author are automatically mailed. Please don't automatically ignore these emails, ok?
If you get a review request, please treat it as a very high priority task. There's another person, who is nervous and has hard time doing something else than waiting for your review.

At the beginning:
    If you see the review request email, but you are busy and you wouldn't quickly do the review,
    add a comment asking the author to assign someone else;
    that's fine, it's better if someone else does the review quickly.

Now complete the following reviewer's checklist:
    - check that the change description makes sense and is descriptive,
    - check that the change description references a Jira issue, if there is one,
    - check if you understand the change:
    - if you don't understand the change, because you don't have enough knowledge about changed code or used frameworks, just write it in a comment and proceed,
    - if you don't understand the change, because it's too complicated for a human to understand, ask the author to simplify it, maybe split into more smaller changes,
    - if you think that the change can be made way simpler, way better etc., ask the author to do it,
    - if you think that the change can be made a bit simpler, a bit better etc., but needs a substantial rewrite of the change, do not write anything,
    - check proper escaping in Jinja templates, if they are touched by the change,
    - you don't need to test (run the project) whether the change actually does what it is expected to do, but if you like, you can checkout the code with the change using the command shown by Gerrit. The command does not change the revision your current branch points to, just checks out into an unnamed branch.
    - finally, check that the code looks good, that is correctly formatted, obeys coding standards and does not have too long lines (should be marked in Gerrit).
Remember that you can also add comments inline, in the reviewed code, by double-clicking on a line.
