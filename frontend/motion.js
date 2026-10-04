// motion.js — Global Motion, Spotlight & Interaction Engine for Trademark DSS

export function initMotion() {
    const isReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isFinePointer = window.matchMedia("(pointer: fine)").matches;

    // 1. Cursor Follow Spotlight
    let cursorGlow = document.getElementById("cursorGlow");
    if (!cursorGlow) {
        cursorGlow = document.createElement("div");
        cursorGlow.id = "cursorGlow";
        cursorGlow.className = "cursor-glow";
        cursorGlow.setAttribute("aria-hidden", "true");
        document.body.prepend(cursorGlow);
    }

    if (!isReducedMotion && isFinePointer && cursorGlow) {
        let targetX = -500, targetY = -500;
        let currX = -500, currY = -500;
        let isMoving = false;

        window.addEventListener("pointermove", (e) => {
            targetX = e.clientX;
            targetY = e.clientY;
            if (!isMoving) {
                cursorGlow.style.opacity = "1";
                isMoving = true;
            }
        }, { passive: true });

        window.addEventListener("pointerleave", () => {
            cursorGlow.style.opacity = "0";
            isMoving = false;
        });

        function animateCursor() {
            currX += (targetX - currX) * 0.12;
            currY += (targetY - currY) * 0.12;
            cursorGlow.style.transform = `translate3d(${currX}px, ${currY}px, 0) translate(-50%, -50%)`;
            requestAnimationFrame(animateCursor);
        }
        requestAnimationFrame(animateCursor);
    }

    // 2. Scroll Progress Bar
    let scrollProgress = document.getElementById("scrollProgress");
    if (!scrollProgress) {
        scrollProgress = document.createElement("div");
        scrollProgress.id = "scrollProgress";
        scrollProgress.className = "scroll-progress";
        scrollProgress.setAttribute("aria-hidden", "true");
        document.body.prepend(scrollProgress);
    }

    function onScroll() {
        const scrollY = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = docHeight > 0 ? (scrollY / docHeight) * 100 : 0;
        if (scrollProgress) {
            scrollProgress.style.width = `${progress}%`;
        }

        const header = document.querySelector(".landing-header, .topbar");
        if (header) {
            if (scrollY > 30) {
                header.classList.add("scrolled");
            } else {
                header.classList.remove("scrolled");
            }
        }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    // 3. Card Spotlight Follow (--mx, --my)
    if (!isReducedMotion && isFinePointer) {
        function attachSpotlights() {
            const cards = document.querySelectorAll(".card, .auth-card, .disclaimer-modal, .bento-card, .use-case-card, .pipeline-step-card, .brand, .safety-panel");
            cards.forEach(card => {
                if (!card.dataset.spotlightBound) {
                    card.dataset.spotlightBound = "true";
                    card.addEventListener("pointermove", (e) => {
                        const rect = card.getBoundingClientRect();
                        card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
                        card.style.setProperty("--my", `${e.clientY - rect.top}px`);
                    }, { passive: true });
                }
            });
        }
        attachSpotlights();
        // Re-attach for dynamic cards (e.g. results, issues, adversarial cards)
        const observer = new MutationObserver(() => attachSpotlights());
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // 4. Magnetic Button Follow
    if (!isReducedMotion && isFinePointer) {
        function attachMagneticButtons() {
            const magneticBtns = document.querySelectorAll(".submit-btn, .new-btn, .auth-action-btn, .btn-hero-primary, .btn-hero-secondary, .btn-gradient, .btn-outline, .disclaimer-agree-btn, .download-btn, .nav-btn-create, .nav-btn-signin");
            magneticBtns.forEach(btn => {
                if (!btn.dataset.magneticBound) {
                    btn.dataset.magneticBound = "true";
                    btn.addEventListener("mousemove", (e) => {
                        const rect = btn.getBoundingClientRect();
                        const x = e.clientX - rect.left - rect.width / 2;
                        const y = e.clientY - rect.top - rect.height / 2;
                        btn.style.transform = `translate(${x * 0.14}px, ${y * 0.14}px)`;
                    });
                    btn.addEventListener("mouseleave", () => {
                        btn.style.transform = "";
                    });
                }
            });
        }
        attachMagneticButtons();
        const mutObs = new MutationObserver(() => attachMagneticButtons());
        mutObs.observe(document.body, { childList: true, subtree: true });
    }

    // 5. Scroll Reveal IntersectionObserver
    if (!isReducedMotion && "IntersectionObserver" in window) {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.05, rootMargin: "60px 0px -20px 0px" });

        function observeReveals() {
            document.querySelectorAll(".reveal:not(.visible)").forEach(el => revealObserver.observe(el));
        }
        observeReveals();
        const revealMutObs = new MutationObserver(() => observeReveals());
        revealMutObs.observe(document.body, { childList: true, subtree: true });
    } else {
        document.querySelectorAll(".reveal").forEach(el => el.classList.add("visible"));
    }
}

// Auto-run if DOM loaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMotion);
} else {
    initMotion();
}
