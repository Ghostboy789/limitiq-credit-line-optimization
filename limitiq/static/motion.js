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
        scrub: 0.65,
      },
    });
  }

  const cards = gsap.utils.toArray("[data-card-stack] .track-card", root);
  const media = gsap.matchMedia();
  media.add("(min-width: 981px)", () => {
    const heroCopy = root.querySelector(".landing-hero-copy");
    if (heroCopy) {
      gsap.to(heroCopy, {
        yPercent: -8,
        opacity: 0.84,
        ease: "none",
        scrollTrigger: {
          trigger: ".landing-hero",
          start: "top top",
          end: "bottom top",
          scrub: 0.55,
        },
      });
    }
    cards.slice(0, -1).forEach((card, index) => {
      gsap.to(card, {
        opacity: 0.48,
        scale: 0.94 + index * 0.02,
        ease: "none",
        scrollTrigger: {
          trigger: cards[index + 1],
          start: "top 82%",
          end: "top 30%",
          scrub: 0.5,
        },
      });
    });
  });

  gsap.utils
    .toArray(
      ".decision-bento > article, .portfolio-ledger-grid > div, .landing-charts > *, .reviewer-copy, .review-carousel",
      root,
    )
    .forEach((item, index) => {
      gsap.fromTo(
        item,
        { opacity: 0.72, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.85,
          delay: (index % 3) * 0.04,
          ease: "power3.out",
          scrollTrigger: { trigger: item, start: "top 88%", once: true },
        },
      );
    });

  window.addEventListener("load", () => ScrollTrigger.refresh(), { once: true });
})();
