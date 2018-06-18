const checkbox = document.querySelector('.checkmark');

agreeToTermsEvt = event => {
	checkbox.removeEventListener('transitionend', agreeToTermsEvt);
	slideLeft();
	document.querySelector('nav').classList.add('nav-visible');
}

agreeToTerms = event => {
	checkbox.removeEventListener('click', agreeToTerms);
	checkbox.addEventListener('transitionend', agreeToTermsEvt)
}

checkbox.addEventListener('click', agreeToTerms)