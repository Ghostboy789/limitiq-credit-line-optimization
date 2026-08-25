const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const liveStatus = document.querySelector("[data-live-status]");
const announce = (message) => {
  if (liveStatus) liveStatus.textContent = message;
};

const markNavigating = () => document.documentElement.classList.add("is-navigating");
const clearNavigationState = () => {
  document.documentElement.classList.remove("is-navigating");
  document.querySelectorAll("[data-busy-original]").forEach((button) => {
    button.textContent = button.dataset.busyOriginal;
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.classList.remove("is-busy");
    delete button.dataset.busyOriginal;
  });
};
window.addEventListener("pageshow", clearNavigationState);

const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector("#primary-nav");

if (toggle && nav) {
  const setNavOpen = (open) => {
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    toggle.querySelector("span").textContent = open ? "Close" : "Menu";
    nav.classList.toggle("open", open);
  };
  toggle.addEventListener("click", () => {
    setNavOpen(toggle.getAttribute("aria-expanded") !== "true");
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) setNavOpen(false);
  });
  document.addEventListener("click", (event) => {
    if (toggle.getAttribute("aria-expanded") === "true" && !event.target.closest(".topbar")) {
      setNavOpen(false);
    }
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
      setNavOpen(false);
      toggle.focus();
    }
  });
  window.matchMedia("(min-width: 1181px)").addEventListener("change", (event) => {
    if (event.matches) setNavOpen(false);
  });
}

document.querySelectorAll("[data-ccy-select]").forEach((select) => {
  select.addEventListener("change", () => {
    const url = new URL(window.location.href);
    url.searchParams.set("ccy", select.value);
    markNavigating();
    window.location.href = url.toString();
  });
});

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const label = input.closest("label")?.querySelector("span");
    const drop = input.closest(".file-drop");
    const file = input.files?.[0];
    if (!label || !file) {
      input.setCustomValidity("");
      drop?.classList.remove("valid", "invalid");
      return;
    }
    const maxBytes = Number(input.dataset.maxBytes) || 5 * 1024 * 1024;
    const invalid = !/\.csv$/i.test(file.name) || file.size > maxBytes;
    let message = `${file.name} · ${(file.size / 1048576).toFixed(1)} MB`;
    if (invalid) {
      message += " · choose a CSV within the stated size limit";
    }
    input.setCustomValidity(invalid ? "Choose a CSV file within the stated size limit." : "");
    drop?.classList.toggle("invalid", invalid);
    drop?.classList.toggle("valid", !invalid);
    label.textContent = message;
    announce(message);
  });
});

document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", () => {
    if (!form.checkValidity()) return;
    const button = form.querySelector("button[type='submit'][data-busy-label]");
    if (button) {
      button.dataset.busyOriginal = button.textContent;
      button.textContent = button.dataset.busyLabel;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.classList.add("is-busy");
    }
    markNavigating();
    if (form.hasAttribute("data-download-form")) window.setTimeout(clearNavigationState, 12000);
  });
});

document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest("a[href]");
  if (!link || link.target || link.hasAttribute("download")) return;
  const url = new URL(link.href, window.location.href);
  if (url.origin !== window.location.origin) return;
  if (url.pathname.startsWith("/downloads/") || url.pathname.endsWith(".csv") || url.searchParams.get("download") === "true") return;
  if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return;
  markNavigating();
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

function renderPalette(items, status = "ready") {
  paletteResults.textContent = "";
  if (status !== "ready") {
    const state = document.createElement("p");
    state.className = "palette-empty";
    state.textContent = status === "loading" ? "Searching…" : "Search is unavailable. Try again.";
    paletteResults.appendChild(state);
    return;
  }
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
      markNavigating();
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
  paletteResults.setAttribute("aria-busy", "true");
  renderPalette([], "loading");
  fetch(`/api/search?q=${encodeURIComponent(q)}`, { signal: paletteController.signal })
    .then((response) => response.json())
    .then((data) => {
      paletteResults.setAttribute("aria-busy", "false");
      activeIndex = 0;
      const items = data.results || [];
      renderPalette(items);
      markActive();
      announce(`${items.length} search result${items.length === 1 ? "" : "s"}`);
    })
    .catch((error) => {
      if (error.name !== "AbortError") {
        paletteResults.setAttribute("aria-busy", "false");
        renderPalette([], "error");
        announce("Search is unavailable. Try again.");
      }
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
    markNavigating();
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

document.querySelectorAll("[data-print]").forEach((button) => {
  button.addEventListener("click", () => window.print());
});

const reviewCarousel = document.querySelector("[data-review-carousel]");
const reviewSlides = reviewCarousel ? [...reviewCarousel.querySelectorAll("[data-review-slide]")] : [];
const reviewDots = reviewCarousel ? [...reviewCarousel.querySelectorAll(".review-dots i")] : [];
const reviewPrevious = document.querySelector("[data-review-prev]");
const reviewNext = document.querySelector("[data-review-next]");
let reviewIndex = 0;

function showReview(index) {
  if (!reviewSlides.length) return;
  reviewIndex = (index + reviewSlides.length) % reviewSlides.length;
  reviewSlides.forEach((slide, position) => { slide.hidden = position !== reviewIndex; });
  reviewDots.forEach((dot, position) => dot.classList.toggle("active", position === reviewIndex));
  const role = reviewSlides[reviewIndex].querySelector("p")?.textContent || "Reviewer";
  announce(`${role} question, ${reviewIndex + 1} of ${reviewSlides.length}`);
}

if (reviewCarousel && reviewPrevious && reviewNext && reviewSlides.length) {
  reviewPrevious.addEventListener("click", () => showReview(reviewIndex - 1));
  reviewNext.addEventListener("click", () => showReview(reviewIndex + 1));
  reviewCarousel.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") showReview(reviewIndex - 1);
    if (event.key === "ArrowRight") showReview(reviewIndex + 1);
  });
}

const jumpLinks = [...document.querySelectorAll("[data-jump-nav] a[href^='#']")];
if (jumpLinks.length && "IntersectionObserver" in window) {
  const jumpSections = jumpLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);
  const jumpObserver = new IntersectionObserver(
    (entries) => {
      const current = entries.find((entry) => entry.isIntersecting);
      if (!current) return;
      jumpLinks.forEach((link) => {
        if (link.getAttribute("href") === `#${current.target.id}`) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    },
    { rootMargin: "-28% 0px -62%", threshold: 0 },
  );
  jumpSections.forEach((section) => jumpObserver.observe(section));
}

document.querySelectorAll(".governance-tracks details").forEach((track) => {
  track.addEventListener("toggle", () => {
    if (!track.open) return;
    track.parentElement.querySelectorAll("details[open]").forEach((sibling) => {
      if (sibling !== track) sibling.open = false;
    });
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
