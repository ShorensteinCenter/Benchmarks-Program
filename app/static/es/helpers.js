/* Tag a form field as valid or invalid */
const tagField = (elt, valid) => {
    if (valid) {
        elt.classList.remove('invalid');
        elt.parentElement.classList.remove('invalid');
        elt.classList.add('valid');
        elt.parentElement.classList.add('valid');
    }
    else {
        elt.classList.remove('valid');
        elt.parentElement.classList.remove('valid');
        elt.classList.add('invalid');
        elt.parentElement.classList.add('invalid');
    }
}

/* Validate a form element on the client side
    Has the side-effect of applying valid/invalid classes */
const clientSideValidateField = elt => {
    const 
        type = elt.getAttribute('custom_type'),
        value = elt.value;
    let valid = true;
    if (type == "key")
        valid = (value.length !== 0 && value.indexOf('-us') !== -1);
    else if (type == "email") {
        valid = (value.length !== 0 && 
            value.indexOf('@') !== -1 && value.indexOf('.') !== -1);
    }
    else
        valid = value.length !== 0;
    tagField(elt, valid);
    return valid;
}

/* Validates a form elements on the client side
    slightly inefficiently written so that the whole loop will execute
    and tag each input as valid or invalid as a side effect.
    Client-side validation is not performed for radio buttons and
    checkboxes due to limitations around Bootstrap's custom styling
    implementation. */
const clientSideValidateForm = form => {
    const elts = form.querySelectorAll(
        'input:not(.disabled-elt), select:not(.disabled-elt)');
    let valid = true;
    for (let i = 0; i < elts.length; ++i) {
        const validity = clientSideValidateField(elts[i])
        if (!validity)
            valid = false;
    }
    return valid;
}

/* Monitors form elements and automatically performs client-side validation
    whenever a user stops typing */
const inputs = document.querySelectorAll(
    '.form-input-wrapper:not(.enter-stats) input, .form-input-wrapper select');
for (let i = 0; i < inputs.length; ++i) {
    const input = inputs[i];
    if (input.tagName == 'INPUT') {
        input.addEventListener(
            'blur', e => clientSideValidateField(e.currentTarget));
    }
    else {
        input.addEventListener(
            'change', e => clientSideValidateField(e.currentTarget))
    }
}

/* Disables an elt or a nodelist of elts */
const disable = elts => {
    if (NodeList.prototype.isPrototypeOf(elts)) {
        for (let i = 0; i < elts.length; ++i)
            elts[i].classList.add('disabled-elt');
    }
    else
        elts.classList.add('disabled-elt');
}

/* Enables an elt or a nodelist of elts */
const enable = elts => {
    if (NodeList.prototype.isPrototypeOf(elts)) {
        for (let i = 0; i < elts.length; ++i)
            elts[i].classList.remove('disabled-elt');
    }
    else
        elts.classList.remove('disabled-elt');
}
 /* Debouncing helper function for event listeners.
    See codeburst.io/throttling-and-debouncing-in-javascript-646d076d0a44 */
const debounced = (delay, fn) => {
    let timerId;
    return (...args) => {
        if (timerId) {
            clearTimeout(timerId);
        }
        timerId = setTimeout(() => {
            fn(...args);
            timerId = null;
        }, delay);
    }
}

/* Value of csrf token to protect against cross-site forgery attacks */
const csrfToken = document.querySelector('meta[name=csrf-token]').content;