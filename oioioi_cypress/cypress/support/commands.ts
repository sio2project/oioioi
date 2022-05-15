// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })

Cypress.Commands.add("hideDjangoToolbar", () => {
    cy.get('body').then((body) => {
        if (body.find('#djHideToolBarButton').length > 0) {
            cy.get('#djHideToolBarButton').click()
        }
    })
})

Cypress.Commands.add("login", (user: OIOIOI.User) => {
    cy.visit("/")

    cy.get('.username').click()

    cy.get('#navbar-login-input').type(user.username)
    cy.get(':nth-child(4) > .form-control').type(user.password)
    cy.get('#navbar-login > .btn-primary').click()
})
