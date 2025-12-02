document.addEventListener('DOMContentLoaded', (event) => {
    const fadeOutButton = document.getElementById('fade-out-button');
    const body = document.querySelector('body');

    if (fadeOutButton) {
        fadeOutButton.addEventListener('click', () => {
            body.classList.add('fade-out');
        });
    }
});