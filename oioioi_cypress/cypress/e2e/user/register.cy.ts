/// <reference types="cypress" />

import { v4 as uuidv4 } from "uuid";

context("Simple user operations", () => {
    before(() => {
        cy.visit("/");
        cy.hideDjangoToolbar();
        cy.enLang();
    });

    it("Register new user", () => {
        cy.fixture("credentials").then((data) => {
            // Unique username is required, because deleting a user prevents
            // registering a new account with the same username, which
            // breaks this test if ran multiple times
            data.user.username = getUniqueUsername();
            registerNewUser(data.user);
            checkIfCanLogIn(data.user);
            tryRemovingUser(data.user, false);
            tryRemovingUser(data.user);
        });
    });

    it("Login as admin", () => {
        cy.fixture("credentials").then((data) => {
            checkIfCanLogIn(data.admin);
        });
    });
});

const getUniqueUsername = () => {
    return "test_username_" + uuidv4().substring(20).replaceAll('-', '_');
};

const registerNewUser = (user_info: OIOIOI.User) => {
    visitRegistrationSite();
    cy.get('.oioioi-form__container').within(() => {
        fillRegistrationForm(user_info);
        cy.get('button[type="submit"]').first().click();
    });
};

const visitRegistrationSite = () => {
    cy.get('.username').click();
    cy.get('#navbar-login').within(() => {
        cy.get('a[role="button"]').click();
    });
};

const fillRegistrationForm = (user_info: OIOIOI.User) => {
    const form_text_map = new Map<string, string>([
        ['#id_username',    user_info.username],
        ['#id_first_name',  user_info.first_name],
        ['#id_last_name',   user_info.last_name],
        ['#id_email',       user_info.email],
        ['#id_password1',   user_info.password],
        ['#id_password2',   user_info.password],
    ]);

    for (let [field, value] of form_text_map) {
        cy.get(field).type(value);
    }

    cy.get('#id_terms_accepted').check();

    // https://django-simple-captcha.readthedocs.io/en/latest/advanced.html#captcha-test-mode
    cy.get('#id_captcha_1').type('PASSED');
};

const checkIfCanLogIn = (user: OIOIOI.User) => {
    cy.login(user);
    checkUserData(user);
};

const checkUserData = (user: OIOIOI.User) => {
    gotoEditProfile();

    const profile_form = new Map<string, string>([
        ['#id_username',    user.username],
        ['#id_first_name',  user.first_name],
        ['#id_last_name',   user.last_name],
        ['#id_email',       user.email],
    ]);

    for (let [field, value] of profile_form) {
        // Value can be undefined when fixture is incomplete and we want
        // it to be incomplete. E.g. admin_admin.json is missing
        // first and last name just like extra/dbdata/default_admin.json
        // which is used as a default data.
        if (value !== undefined) {
            cy.get(field).should('have.value', value);
        }
    }
};

const tryRemovingUser = (user: OIOIOI.User, shouldRemove: boolean = true) => {
    gotoEditProfile();
    cy.contains('Delete').click();

    cy.get('form[method="post"]').within(() => {
        cy.get('input[name="auth-password"]').type(user.password);
        cy.contains(shouldRemove ? 'Yes' : 'No').click();
    });

    if (shouldRemove) {
        cy.login(user, false);
        cy.get('.card').should(($page) => {
            expect($page).to.contain('Please enter a correct username and password.');
        });
    }
    else {
        checkUserData(user);
    }
};

const gotoEditProfile = () => {
    cy.visit('/edit_profile/');
};
