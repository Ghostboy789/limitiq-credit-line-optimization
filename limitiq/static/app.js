const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector("#primary-nav");

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    nav.classList.toggle("open", !open);
  });
}

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const label = input.closest("label")?.querySelector("span");
    if (label && input.files?.length) label.textContent = input.files[0].name;
  });
});

if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
    { rootMargin: "0px 0px -8%", threshold: 0.08 },
  );
  document.querySelectorAll("main > section, main > .notice, main > .metric-grid, main > .two-column, main > .dashboard-grid").forEach((item) => {
    item.classList.add("reveal");
    observer.observe(item);
  });
}
