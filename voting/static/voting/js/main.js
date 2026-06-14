function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        let date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax";
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.remove("no-transition");
});

window.toggleTheme = function() {
    const isDark = document.body.classList.toggle('dark-theme');
    const value = isDark ? 'dark' : 'light';
    localStorage.setItem('theme', value);
    setCookie('theme', value, 365);
};

window.toggleAccessibility = function() {
    const isAccessible = document.body.classList.toggle('accessible-mode');
    const value = isAccessible ? 'enabled' : 'disabled';
    localStorage.setItem('accessibility', value);
    setCookie('accessibility', value, 365);
};

function toggleDropdown(event) {
    event.stopPropagation();
    document.getElementById('userMenu').classList.toggle('show');
}

window.addEventListener('click', () => {
    const menu = document.getElementById('userMenu');
    if (menu) menu.classList.remove('show');
});