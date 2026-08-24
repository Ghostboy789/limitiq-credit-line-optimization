(() => {
  const root = document.querySelector("[data-landing]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!root || reduceMotion || !window.gsap || !window.ScrollTrigger) return;

  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);

  const words = gsap.utils.toArray("[data-scrub-word]", root);
  if (words.length) {
    gsap.set(words, { opacity: 0.18, y: 10 });
    gsap.to(words, {
      opacity: 1,
      y: 0,
      ease: "none",
      stagger: 0.08,
      scrollTrigger: {
        trigger: "[data-scrub-copy]",
        start: "top 84%",
        end: "bottom 48%",
        scrub: true,
      },
    });
  }

  const cards = gsap.utils.toArray("[data-card-stack] .track-card", root);
  const media = gsap.matchMedia();
  media.add("(min-width: 981px)", () => {
    cards.slice(0, -1).forEach((card, index) => {
      gsap.to(card, {
        opacity: 0.48,
        scale: 0.94 + index * 0.02,
        ease: "none",
        scrollTrigger: {
          trigger: cards[index + 1],
          start: "top 82%",
          end: "top 30%",
          scrub: true,
        },
      });
    });
  });

  window.addEventListener("load", () => ScrollTrigger.refresh(), { once: true });
})();
