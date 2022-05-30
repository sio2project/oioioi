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
    cy.get('#navbar-login').within(() => {
        cy.get('input[name="auth-username"]').type(user.username);
        cy.get('input[name="auth-password"]').type(user.password);
        cy.get('button[type="submit"]').click();
    });
});

Cypress.Commands.add("setLang", (language: string) => {
    cy.visit("/");
    cy.get(".oioioi-navbar__lang").click();
    cy.get(".lang-select").contains(language).click();
});

Cypress.Commands.add("enLang", () => {
    cy.setLang("English");
});

Cypress.Commands.add("plLang", () => {
    cy.setLang("Polski");
});
