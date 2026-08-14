const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const liveStatus = document.querySelector("[data-live-status]");
const announce = (message) => {
  if (liveStatus) liveStatus.textContent = message;
};

const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector("#primary-nav");

if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    nav.classList.toggle("open", !open);
  });
}

document.querySelectorAll("[data-ccy-select]").forEach((select) => {
  select.addEventListener("change", () => {
    const url = new URL(window.location.href);
    url.searchParams.set("ccy", select.value);
    window.location.href = url.toString();
  });
});

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const label = input.closest("label")?.querySelector("span");
    const file = input.files?.[0];
    if (!label || !file) return;
    const megabyte = 5 * 1024 * 1024;
    let message = `${file.name} · ${(file.size / 1048576).toFixed(1)} MB`;
    if (!/\.csv$/i.test(file.name) || file.size > megabyte) {
      message += " · check the UTF-8 CSV format and 5 MB limit";
    }
    label.textContent = message;
    announce(message);
  });
});

const paletteTrigger = document.querySelector("[data-palette-open]");
const palette = document.querySelector("#palette");
const paletteInput = palette?.querySelector("input");
const paletteResults = palette?.querySelector("[data-palette-results]");
const paletteClose = palette?.querySelector("[data-palette-close]");
const pageSiblings = palette
  ? [...document.body.children].filter(
    (item) => item !== palette && item.tagName !== "SCRIPT" && !item.matches("[data-live-status]"),
  )
  : [];

function renderPalette(items) {
  paletteResults.textContent = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "palette-empty";
    empty.textContent = "No matching accounts or pages.";
    paletteResults.appendChild(empty);
    return;
  }
  items.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "palette-item";
    button.setAttribute("role", "option");
    button.id = `palette-option-${index}`;
    button.tabIndex = -1;
    const type = document.createElement("small");
    type.textContent = item.type;
    const label = document.createElement("strong");
    label.textContent = item.label;
    const sublabel = document.createElement("span");
    sublabel.textContent = item.sublabel;
    button.append(type, label, sublabel);
    button.addEventListener("click", () => {
      window.location.href = item.href;
    });
    paletteResults.appendChild(button);
  });
}

let paletteTimer = null;
let activeIndex = 0;
let paletteController = null;

function searchPalette() {
  const q = paletteInput.value.trim();
  paletteController?.abort();
  paletteController = new AbortController();
  fetch(`/api/search?q=${encodeURIComponent(q)}`, { signal: paletteController.signal })
    .then((response) => response.json())
    .then((data) => {
      activeIndex = 0;
      const items = data.results || [];
      renderPalette(items);
      markActive();
      announce(`${items.length} search result${items.length === 1 ? "" : "s"}`);
    })
    .catch((error) => {
      if (error.name !== "AbortError") renderPalette([]);
    });
}

function markActive() {
  const items = paletteResults.querySelectorAll(".palette-item");
  items.forEach((item, index) => {
    const active = index === activeIndex;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
  });
  paletteInput.setAttribute("aria-activedescendant", items[activeIndex]?.id || "");
}

function openPalette() {
  palette.hidden = false;
  palette.classList.add("open");
  pageSiblings.forEach((item) => { item.inert = true; });
  paletteInput.value = "";
  searchPalette();
  paletteInput.focus();
}

function closePalette() {
  paletteController?.abort();
  palette.classList.remove("open");
  palette.hidden = true;
  pageSiblings.forEach((item) => { item.inert = false; });
  paletteInput.removeAttribute("aria-activedescendant");
  paletteTrigger.focus();
}

if (paletteTrigger && palette && paletteInput && paletteResults && paletteClose) {
  paletteTrigger.addEventListener("click", openPalette);
  paletteClose.addEventListener("click", closePalette);
  paletteInput.addEventListener("input", () => {
    clearTimeout(paletteTimer);
    paletteTimer = setTimeout(searchPalette, 180);
  });
  paletteInput.addEventListener("keydown", (event) => {
    const items = paletteResults.querySelectorAll(".palette-item");
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      markActive();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      markActive();
    } else if (event.key === "Enter" && items[activeIndex]) {
      event.preventDefault();
      items[activeIndex].click();
    }
  });
  palette.addEventListener("click", (event) => {
    if (event.target === palette) closePalette();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && palette.classList.contains("open")) {
      event.preventDefault();
      closePalette();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (palette.classList.contains("open")) closePalette();
      else openPalette();
    }
    if (event.key === "Tab" && palette.classList.contains("open")) {
      const first = paletteClose;
      const last = paletteInput;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
}

const toTop = document.querySelector(".to-top");
if (toTop) {
  const showToTop = () => toTop.classList.toggle("visible", window.scrollY > 600);
  window.addEventListener("scroll", showToTop, { passive: true });
  showToTop();
  toTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion ? "auto" : "smooth" });
  });
}

const sortParams = new URLSearchParams(window.location.search);
const sortKey = sortParams.get("sort") || "pd";
const sortDirection = sortParams.get("direction") === "asc" ? "asc" : "desc";
document.querySelectorAll("th[data-sort]").forEach((th) => {
  if (th.dataset.sort === sortKey) {
    const arrow = document.createElement("span");
    arrow.className = "sort-arrow";
    arrow.textContent = sortDirection === "asc" ? "▲" : "▼";
    th.querySelector("a").appendChild(arrow);
  }
});

document.querySelectorAll("tr[data-href]").forEach((row) => {
  row.addEventListener("click", (event) => {
    if (event.target.closest("a, button, input, select")) return;
    window.location.href = row.dataset.href;
  });
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const fallbackLabel = button.dataset.copyLabel || button.textContent;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = "Copied";
      announce(`${button.dataset.copy} copied`);
      setTimeout(() => { button.textContent = fallbackLabel; }, 1600);
    } catch {
      announce("Copy failed. Select the account identifier and copy it manually.");
    }
  });
});

if (!prefersReducedMotion && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
    { rootMargin: "0px 0px -8%", threshold: 0.08 },
  );
  document.querySelectorAll("main > section, main > .notice, main > .metric-grid, main > .two-column, main > .dashboard-grid").forEach((item) => {
    item.classList.add("reveal");
    observer.observe(item);
  });
}
