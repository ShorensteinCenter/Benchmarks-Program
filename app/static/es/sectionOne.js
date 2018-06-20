const checkbox = document.querySelector('.checkbox-container');

/* slideLeft and fade in the nav, once, upon checkbox animation end */
const agreeToTerms = () => {
	setTimeout(() => {
		slideLeft();
		document.querySelector('nav').classList.add('nav-visible');
	}, 500);
}

checkbox.addEventListener('mousedown', agreeToTerms, {once: true})