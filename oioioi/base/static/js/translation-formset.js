// Constructs an object which will control behaviour of translations formset
// (a set of forms containing different translations of some content).
// You may want to override some of it's parameters - pass them in a dictionary
// as the first argument:
//     - 'select': a jQuery-wrapped HTMLSelectElement that is used to choose a displayed translation,
//     - 'formGetter': a function returning forms (as jQuery objects) for a given language,
//     - 'requiredFieldsSelector': a CSS selector string, matching the inputs of required fields.
function TranslationFormset(parameters) {
    for (var parameter in parameters) {
        if (typeof(this[parameter]) === 'undefined') {
            throw "Sorry, parameter '" + parameter + "' passed to TranslationFormset is not recognized.";
        } else {
            this[parameter] = parameters[parameter];
        }
    }

    var tFormset = this;

    this.select.change(function() {
        if (!this.value) {
            tFormset.hideTranslation(tFormset.currentLang);
        } else {
            tFormset.showTranslation(this.value);
        }
    });

    // For each form in a formset, Django adds a checkbox indicating deletion of the
    // form's instance. We hide the checkbox (along with it's parent-label) from
    // the user and check/uncheck it in TranslationFormset's internal functions.
    $('input[name*="DELETE"]').parent().hide();


    // Find the forms that should be visible (translations already created by user) according
    // to POST data and display them - with forms containing errors at the beginning.
    var notDeletedForms = [];
    var notDeletedFormsWithErrors = [];

    this.forms().each(function(index, form) {
        var $form = $(form);

        var requiredFields = $form.find(tFormset.requiredFieldsSelector);
        form.tf__requiredFields = requiredFields.get();

        tFormset.computeFormDeletion($form);
        requiredFields.change(tFormset.computeFormDeletion.bind(tFormset, $form));

        if (!tFormset.formDeleted($form)) {
            if ($form.find('.has-error').length > 0) {
                notDeletedFormsWithErrors.push($form);
            } else {
                notDeletedForms.push($form);
            }
        }
    });

    // Forms for created translations, the ones containing errors at the beginning.
    notDeletedForms = notDeletedFormsWithErrors.concat(notDeletedForms);

    notDeletedForms.forEach(function(form) {
        var lang = form.data('lang');
        tFormset.addTranslation(lang);
    });

    // The form from the first column is always required.
    this.formDeleted($('.first-column'), false);
}

$.extend(TranslationFormset.prototype, {
    select: $('#translation-select'),
    forms: function (lang) { return lang ? $('#form-' + lang) : $('[id^=form-]'); },
    requiredFieldsSelector: '',
    currentLang: '',

    hideTranslation: function(lang) {
        if (lang) {
            this.forms(lang).css('display', 'none');
        }
        if (lang === this.currentLang) {
            this.currentLang = '';
        }
    },
    showTranslation: function(lang) {
        var form = this.forms(lang);

        // Hide previously displayed form - only one form per column.
        this.hideTranslation(this.currentLang);

        form.css('display', 'block');
        this.select.val(lang);
        this.currentLang = lang;
    },
    addTranslation: function(lang) {
        // Mark new languages' form as not deleted.
        this.formDeleted(this.forms(lang), false);

        // If there's an empty column - display it with the new translation form.
        if (this.currentLang === '') {
            this.showTranslation(lang);
        }
    },
    formDeleted: function(form, value) {
        if (arguments.length < 2) {
            return form.find('input[name*="DELETE"]').prop('checked');
        } else {
            return form.find('input[name*="DELETE"]').prop('checked', value);
        }
    },
    computeFormDeletion: function(form) {
        if (form.get(0).tf__requiredFields.every(this.fieldIsEmpty)) {
            this.formDeleted(form, true);
        } else if (this.formDeleted(form)) {
            this.formDeleted(form, false);
        }
    },
    fieldIsEmpty: function(field) {
        return !field.value;
    }
});
