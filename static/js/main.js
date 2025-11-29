console.log("Main.js cargado correctamente!");

document.addEventListener("DOMContentLoaded", () => {
    // Ejemplo: animación en alertas
    const alerts = document.querySelectorAll(".alert");
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(a => a.classList.add("fade"));
        }, 3000);
    }
});
