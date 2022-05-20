======================
Contributing to OIOIOI
======================

How to create Pull Request
--------------------------

Follow generic guidelines from https://docs.github.com/en/pull-requests/collaborating-with-pull-requests


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
        The files you need are in *oioioi/_locale/locale/<lang>/LC_MESSAGES/*,
        where <lang> is the short version (pl, en, de) of one of the currently supported
        languages defined in the **settings.py** file.
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
