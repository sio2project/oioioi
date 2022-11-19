$(document).ready(function () {
    let password_form_control = document.getElementById('id_confirm_password');
    let password_form_group = password_form_control.parentElement;

    if (!password_form_control.classList.contains('is-invalid'))
        password_form_group.classList.add('d-none');
    $("#id_email").change(function () {
        password_form_group.classList.remove('d-none');
    });
});
