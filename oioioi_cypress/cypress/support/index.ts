// ***********************************************************
// This example support/index.js is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

declare namespace Cypress {
    interface Chainable<Subject = any> {

        // If Django Toolbar is enabled it can hoover some clickable elements, 
        // so we should hide it before each test. By default, it is disabled,
        // but who knows ¯\_(ツ)_/¯
        hideDjangoToolbar(): Chainable<null>

        // User related commands
        login(user: OIOIOI.User): Chainable<null>

        // Language related commands
        setLang(language: string): Chainable<null>
        enLang(): Chainable<null>
        plLang(): Chainable<null>
    }
}

declare namespace OIOIOI {
    interface User {
        username: string,
        first_name: string,
        second_name: string,
        email: string,
        password: string
    }
}

// Import commands.js using ES2015 syntax:
import './commands'

// Alternatively you can use CommonJS syntax:
// require('./commands')
