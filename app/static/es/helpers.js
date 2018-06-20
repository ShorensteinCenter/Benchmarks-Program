/* Transition from one section of the home page to the next */
const slideLeft = () => {
	const 
		slides = document.querySelectorAll('.container-fluid'),
		slide = slides[0],
		slideTransform = slide.style.transform,
		transformVal = slideTransform == null ? -100 :
			+slideTransform.replace(/[^-?\d.]/g, '') - 100;
	for (let i = 0; i < slides.length; ++i)
		slides[i].style.transform = 'translateX(' + transformVal + 'vw)';
}

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
const clientSideValidate = elt => {
	const 
		type = elt.getAttribute('customType'),
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
	and tag each input as valid or invalid as a side effect */
const clientSlideValidateMultiple = form => {
	elts = form.querySelectorAll('input');
	let valid = true;
	for (let i = 0; i < elts.length; ++i) {
		validity = clientSideValidate(elts[i])
		if (!validity)
			valid = false;
	}
	return valid;
}

/* Monitors form elements and automatically performs client-side validation
	whenever a user stops typing */
const formElts = document.querySelectorAll('.form-input-wrapper input');
for (let i = 0; i < formElts.length; ++i) {
	const elt = formElts[i];
	elt.addEventListener('keyup', e => clientSideValidate(e.currentTarget));
}

/* Disables a form */
const disableForm = formElt => {
	const inputs = formElt.querySelectorAll('input');
	for (let i = 0; i < inputs.length; ++i)
		inputs[i].classList.add('disabled');
}

/* Enables a form */
const enableForm = formElt => {
	const inputs = formElt.querySelectorAll('input');
	for (let i = 0; i < inputs.length; ++i)
		inputs[i].classList.remove('disabled');
}

/* Value of csrf token to protect against cross-site forgery attacks */
const csrfToken = document.querySelector('meta[name=csrf-token]').content;