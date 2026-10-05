========================
Webpack and NPM packages
========================

Overview
--------

Initially, this project did not use Webpack or any JavaScript bundling tools. 
All libraries were installed by manually copying their source code into the project and including them with `<script>` tags. 

The project was migrated to use NPM for managing dependencies and Webpack for bundling JavaScript modules. 
While most packages have been migrated to NPM downloads, there is still a significant amount of JavaScript code that is not managed by Webpack. 

For new JavaScript code, it is recommended to write it as a JavaScript file and bundle it using Webpack. 

Webpack setup
-------------

Webpack is configured to bundle our JavaScript code and downloaded packages for browser usage. 
The configuration is designed to work alongside the existing Django application.

Webpack starts with the webserver automatically when using `./easy_toolbox.py run`, but you can also run it manually:
    ::

        $ ./easy_toolbox.py npm run build # generate the production build
        $ ./easy_toolbox.py npm run watch # generate the development build and watch for changes

Managing JavaScript with Webpack
--------------------------------

1. Create a new JavaScript file in the `static` directory inside your Django app.
2. Write your JavaScript code in that file, explicitly importing any necessary libraries.
3. Add the JavaScript file to the `entry` section in `webpack.config.js`.
4. Load the generated JavaScript bundle in your Django template:
    .. code-block:: html

        {% load static %}
        <script src="{% static '[entry-name].bundle.js' %}"></script>

NPM packages
------------

Installing New Packages:
    ::

        $ ./easy_toolbox.py npm install package-name

Importing Packages in JavaScript managed by Webpack:
    .. code-block:: javascript

        import packageName from 'package-name';
        import 'other-package-name';

        // Your JS code

Importing Packages Globally with `<script>` Tags:
    .. code-block:: html

        {% load static %}
        <script src="{% static 'marked/marked.min.js' %}"></script>
        <script src="{% static 'package-name/path-to-dist.js' %}"></script>

    This approach is not recommended for new code but may be necessary for existing code. 
    This works because Django also searches for static files in the `node_modules` directory.

ESLint
------

ESLint is used to enforce coding standards and catch potential issues in JavaScript code.
To run ESLint, use the following command:
    ::

        $ ./easy_toolbox.py eslint