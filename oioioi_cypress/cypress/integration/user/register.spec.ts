/// <reference types="cypress" />

context("Register", () => {
    before(() => {
        cy.visit("/");
        cy.hideDjangoToolbar();
    });

    it("Register new user", () => {

        const user_info: OIOIOI.User = {
            username:       "test_username",
            first_name:     "test_name",
            last_name:      "test_surname",
            email:          "test@test.com",
            password:       "test_password",
        };

        registerNewUser(user_info);
        checkIfCanLoginIn(user_info);
        tryRemovingUserUser(user_info, false);
        tryRemovingUserUser(user_info);
    });
});

let registerNewUser = (user_info: OIOIOI.User) => {

    visitRegistrationSite();

    cy.get('.container').within(() => {
        fillRegistrationForm(user_info);

        // Submit the form.
        cy.get('button[type="submit"]').first().click();
    })
};

let visitRegistrationSite = () => {
    cy.get('.username').click();
    cy.get('#navbar-login > .btn-default').click();
};

let fillRegistrationForm = (user_info: OIOIOI.User) => {

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

let checkIfCanLoginIn = (user: OIOIOI.User) => {
    cy.login(user);
    checkUserData(user);
};

let checkUserData = (user: OIOIOI.User) => {
    gotoEditProfile();

    const profile_form = new Map<string, string>([
        ['#id_username',    user.username],
        ['#id_first_name',  user.first_name],
        ['#id_last_name',   user.last_name],
        ['#id_email',       user.email],
    ]);

    for (let [field, value] of profile_form) {
        cy.get(field).should('have.value', value);
    }
}

let tryRemovingUserUser = (user: OIOIOI.User, shouldRemove: boolean = true) => {
    gotoEditProfile();

    cy.get('.btn-danger').click();
    cy.get('.form-control').type(user.password);

    if (shouldRemove) {
        cy.get('.btn-danger').click();
        cy.login(user);
        cy.get('.well').should(($page) => {
            expect($page).to.contain('Please enter a correct username and password.');
        });
    }
    else {
        cy.get('.btn-group > .btn-default').click();
        checkUserData(user);
    }
}

let gotoEditProfile = () => {
    cy.get('#username').click();
    cy.get('.oioioi-navbar__user > .dropdown > .dropdown-menu > :nth-child(1) > a').click();
}
