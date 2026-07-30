document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-intake-toggle]").forEach((cell) => {
    const checkbox = cell.querySelector("input[type='checkbox']");
    if (!checkbox) return;

    const syncColor = () => {
      cell.style.backgroundColor = checkbox.checked ? cell.dataset.color : "";
    };

    checkbox.addEventListener("change", syncColor);
    syncColor();
  });
});
