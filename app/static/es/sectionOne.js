const checkbox = document.querySelector('.checkbox-container');

/* slideLeft and fade in the nav, once, upon checkbox animation end */
const agreeToTermsEvt = () => {
	slideLeft();
	document.querySelector('nav').classList.add('nav-visible');
}

const agreeToTerms = () => {
	checkbox.removeEventListener('mousedown', agreeToTerms);
	setTimeout(agreeToTermsEvt, 500);
}

checkbox.addEventListener('mousedown', agreeToTerms)