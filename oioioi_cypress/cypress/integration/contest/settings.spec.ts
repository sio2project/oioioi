/// <reference types="cypress" />

import "cypress-file-upload";
import { v4 as uuidv4 } from "uuid";

const TYPE_OPTIONS = {
  parseSpecialCharSequences: false,
  delay: 0,
};

const CONTEST_TYPES = [
  "Simple programming contest",
  "Polish Olympiad in Informatics - Online",
  "Polish Olympiad in Informatics - Onsite",
  "Polish Olympiad in Informatics - Onsite - Finals",
  "Baltic Olympiad in Informatics",
  "Baltic Olympiad in Informatics - online",
  "ACM style contest",
  "ACM style contest (open)",
];

context("Access settings for contest", () => {
  beforeEach(() => {
    loginAsAdmin();
    chooseEnglishLang();
  });

  CONTEST_TYPES.forEach((type: string) => {
    it(`should access settings of ${type}`, () => {
      const name = uuidv4().substring(10);
      addContest(type, name);
      accessSettings(name);
      deleteContest(name);
    });
  });
});

const loginAsAdmin = () => {
  cy.visit("/");
  cy.get(".username").click();

  cy.fixture("credentials").then((data) => {
    cy.get("#navbar-login-input").type(data.user.username);
    cy.get(":nth-child(4) > .form-control").type(data.user.password);
    cy.get("#navbar-login > .btn-primary").click();
  });
};

const chooseEnglishLang = () => {
  cy.visit("/");
  cy.get(".oioioi-navbar__lang").click();
  cy.get(".lang-select").contains("English").click();
};

const addContest = (type: string, name: string) => {
  cy.visit("/admin/contests/contest/add");
  cy.get("#id_controller_name").select(type);
  cy.get("input").get("[name='name']").type(name, TYPE_OPTIONS);
  cy.get(".default").click();
};

const accessSettings = (name: string) => {
  cy.visit(`/c/${name}/admin/contests/contest/${name}/change/`);
  cy.contains("Change contest");
};

const deleteContest = (name: string) => {
  cy.visit(`/c/${name}/admin/contests/contest/${name}/delete`);
  cy.get("button").contains("Yes, I'm sure").click();
  cy.contains(`The contest "${name}" was deleted successfully.`);
};
