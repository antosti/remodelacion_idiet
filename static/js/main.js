document.addEventListener("DOMContentLoaded", () => {
document.querySelectorAll("[data-alert]").forEach((alert) => {
    setTimeout(() => {
    alert.classList.add("opacity-0", "translate-x-8");
    setTimeout(() => alert.remove(), 300);
    }, 4000);
});
});