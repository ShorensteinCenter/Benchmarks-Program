/* Transition from one section of the form to the next */
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