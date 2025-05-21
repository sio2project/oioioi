/// <reference types="cypress" />

import "cypress-file-upload";
import { v4 as uuidv4 } from "uuid";

const TYPE_OPTIONS = {
  parseSpecialCharSequences: false,
  delay: 0,
};

const CONTEST_NAME = uuidv4().substring(10);

context("Submit", () => {
  before(() => {
    loginAsAdmin();
    chooseEnglishLang();
    addContest();
  });

  after(() => {
    deleteContest();
  });

  it("should submit task", () => {
    addProblem();
    submit();
    validateIfStatusOk();
  });
});

const loginAsAdmin = () => {
  cy.visit("/");
  cy.fixture("credentials").then((data) => {
    cy.login(data.admin);
  });
};

const chooseEnglishLang = () => {
  cy.enLang();
};

const addContest = () => {
  cy.visit("/admin/contests/contest/add");
  cy.get("#contest_form").within(() => {
    cy.get("#id_controller_name").select("Simple programming contest");
    cy.get("input").get("[name='name']").type(CONTEST_NAME, TYPE_OPTIONS);
    cy.get("input[name='_save']:visible").click();
  });
};

const addProblem = () => {
  cy.visit(`/c/${CONTEST_NAME}/admin/contests/probleminstance`);
  cy.get("a").contains("Add problem").click();

  cy.fixture("submit").then((data) => {
    cy.get("input[type='file']")
      .attachFile(data.problem.package, {
        subjectType: "drag-n-drop",
      })
      .then(() => {
        cy.get("button").contains("Submit").click();
        cy.contains("Package queued for processing");
      });
  });
};

const submit = () => {
  cy.visit(`/c/${CONTEST_NAME}/submit`);

  cy.fixture("submit").then((data) => {
    cy.get("#id_problem_instance_id").select(data.problem.name);
    cy.get("input[type='file']")
      .attachFile(data.problem.solution, {
        subjectType: "drag-n-drop",
      })
      .then(() => {
        cy.get("button").contains("Submit").click();
        cy.get("div").contains("Pending");
      });
  });
};

const validateIfStatusOk = (attempts = 10) => {
  const message = "Initial tests: OK";

  cy.get(".submission")
    .get("tr")
    .eq(1)
    .then(($div) => {
      if (!$div.text().includes(message) && attempts) {
        cy.reload();
        return cy.wait(2000).then(() => {
          cy.log("Attempts left: " + attempts);
          return validateIfStatusOk(attempts - 1);
        });
      } else if (!attempts) {
        throw new Error("Attempts exceeded.");
      }
    });
};

const deleteContest = () => {
  cy.visit(`/c/${CONTEST_NAME}/admin/contests/contest/${CONTEST_NAME}/delete`);
  cy.get("button").contains("Yes, I'm sure").click();
  cy.contains(`The contest "${CONTEST_NAME}" was deleted successfully.`);
};
