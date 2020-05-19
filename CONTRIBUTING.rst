======================
Contributing to OIOIOI
======================

Checking Out Code for Development
---------------------------------

To access the read-write version of the Git repository:

- If you don't have a SIO2 Project account yet, come and register!
- Then log in to our Gerrit and `upload your SSH public key`__ (which usually is either ~/.ssh/id_dsa.pub or ~/.ssh/id_rsa.pub).
    - If you don't have an SSH public key, generate one using
        ``$ ssh-keygen -t rsa``
- Make sure that your name and email are specified in ~/.gitconfig.
- Now checkout the code
    ``$ git clone ssh://_YOUR_LOGIN_@sio2project.mimuw.edu.pl:29418/oioioi``
- Install the Gerrit commit-msg hook
    ``$ scp -p -P 29418 _YOUR_LOGIN_@sio2project.mimuw.edu.pl:hooks/commit-msg oioioi/.git/hooks/``

__ https://gerrit.sio2project.mimuw.edu.pl/settings/ssh-keys

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


SIO2 Translator's Guide
-----------------------

We use Transifex_ to manage translations.

Why translate?
    It's always better to see an application in you mother tongue.
    No matter how well you speak English, it's always nice to use applications in the language you think in, isn't it?
    And as SIO2 aims to be accessible to everybody around the world, we want it to be translated to as many languages as possible.
    And unfortunately we don't speak that many languages, so we need to rely on your help!
    If you speak a language other than English and think you're capable of translating, try it!
    It's really easy, there is no technical knowledge required and you can get started really fast!

I want to help!
    That's great! Everybody wanting to help will be welcome!
    To start you need to go to our page on Transifex, create an account and start translating!
    Transifex_ has a very comprehensive help, which you may use to learn how to use it.
    You're welcome to translate as many messages you see, and create your own languages!

.. _Transifex: https://www.transifex.com/sio2project/sio2project/

Advice
    The text on the left is the text to translate, and the text on the right is the translated text, that's easy.
    But what to do with strange %(gizmo)s? It's also simple, they are just placeholders which will be changed
    to real words during SIO2 execution. You just need to place them in the same exact form where they should be used in your language.

What to do with plural forms?!
    Plural forms are tricky, and they are not very well explained.
    When a message contains a plural form, it has to be translated into a few different versions.
    English has only 2 (singular and plural), but if your language is more complicated you need to watch out.
    Generally you will have a few text areas to write different plural versions.
    The best way to know where goes which is to find other project translated into that language.
    There is also a small note to the right of each text area, but it may be hard to understand.
    For example for Polish it should be:
+-----------------------+-----------------------+
| English               | Polish                |
+=======================+=======================+
| Ala has %(cats)d cat  | Ala ma jednego kota   |
+------------+----------+-----------------------+
| Ala has %(cats)d cats | Ala ma %(cats)d koty  |
+-----------------------+-----------------------+
|                       | Ala ma %(cats)d kotów |
+-----------------------+-----------------------+

Working with Transifex and SIO2 guide (for developers translating)
    Correcting original English strings
        Unfortunately, Transifex does not allow for editing English strings in its editor.
        They need to be changed in the source files, preferably along with msgid.
        The files you need are in *oioioi/locale/en/LC_MESSAGES/*.
        You can edit only the *.po* files, however if you change msgid (preferable)
        you have to also change it in all the other languages and all the source files the id occurs in.
        The source files are all listed above the strings in the *.po* files.
        Some original strings are also used in unit tests, so if you change them, Hudson will notify about the failed build.
    Applying changes from Transifex
        To apply the changes made to localized strings in Transifex you need to sign in to Hudson
        and launch the 'oioioi-translations-download' job.
        To avoid cluttering the commit list it is preferable to only launch that before deploying changes to production.
    Applying changes to Transifex
        This is done automatically by Hudson when submitting a change.
