document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect) themeSelect.value = savedTheme;

    if (themeSelect) {
        themeSelect.addEventListener('change', (e) => {
            const selectedTheme = e.target.value;
            console.log(selectedTheme)
            localStorage.setItem('theme', selectedTheme);
            setTheme(selectedTheme);
        });
    }
});

function setTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('bg-dark', 'text-white');
        document.querySelectorAll('.card, .form-control, .form-select, .tab-pane')
            .forEach(el => el.classList.add('bg-dark', 'text-white'));
    } else {
        document.body.classList.remove('bg-dark', 'text-white');
        document.querySelectorAll('.card, .form-control, .form-select, .tab-pane')
            .forEach(el => el.classList.remove( 'bg-dark' ,'text-white'));
    }
}