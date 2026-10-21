/* =========================================================
   GRIMFLOT LTD — PUBLIC SITE INTERACTIONS
   Features:
   - Reliable branded preloader
   - Responsive navigation
   - Accessible mobile menu
   - Hero slider and autoplay
   - GSAP scroll reveal animations
   - Reduced-motion support
   ========================================================= */

(() => {
    'use strict';

    const root = document.documentElement;
    const body = document.body;
    const loader = document.querySelector('#site-loader');
    const menu = document.querySelector('[data-primary-menu]');
    const toggle = document.querySelector('[data-menu-toggle]');
    const header = document.querySelector('[data-site-header]');
    const reduceMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
    ).matches;

    let lastFocusedElement = null;

    /* =====================================================
       1. PRELOADER
       ===================================================== */

    if (loader && !loader.dataset.loaderInitialized) {
        loader.dataset.loaderInitialized = 'true';

        const minimumLoaderDuration = 1100;
        const loaderStartedAt = window.performance.now();
        let loaderDismissed = false;
        let loaderFallback = null;

        const hideLoader = () => {
            if (loaderDismissed) return;

            loaderDismissed = true;
            loader.classList.add('is-hidden');
            loader.setAttribute('aria-hidden', 'true');

            if (loaderFallback !== null) {
                window.clearTimeout(loaderFallback);
            }
        };

        const requestLoaderHide = () => {
            const elapsed = window.performance.now() - loaderStartedAt;
            const remaining = Math.max(0, minimumLoaderDuration - elapsed);

            window.setTimeout(hideLoader, remaining);
        };

        // Avoid leaving the loading screen visible indefinitely on a stalled load.
        loaderFallback = window.setTimeout(hideLoader, 4000);

        if (document.readyState === 'complete') {
            requestLoaderHide();
        } else {
            window.addEventListener('load', requestLoaderHide, { once: true });
        }
    }

    /* =====================================================
       1A. INTERNAL PAGE TRANSITIONS
       ===================================================== */

    if (loader && !loader.dataset.navigationLoaderInitialized) {
        loader.dataset.navigationLoaderInitialized = 'true';

        let navigationFallback = null;

        const showNavigationLoader = (destination) => {
            if (navigationFallback !== null) return;

            loader.classList.remove('is-hidden');
            loader.classList.add('is-navigating');
            navigationFallback = window.setTimeout(() => {
                window.location.assign(destination.href);
            }, 1100);
        };

        document.addEventListener('click', (event) => {
            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }

            const link = event.target.closest('a[href]');
            if (!link || link.target || link.hasAttribute('download')) return;

            const destination = new URL(link.href, window.location.href);
            const isSamePageAnchor =
                destination.origin === window.location.origin &&
                destination.pathname === window.location.pathname &&
                destination.search === window.location.search &&
                Boolean(destination.hash);

            if (
                destination.origin !== window.location.origin ||
                destination.protocol !== window.location.protocol ||
                isSamePageAnchor ||
                /^(mailto:|tel:|sms:|whatsapp:)/i.test(link.href)
            ) {
                return;
            }

            event.preventDefault();
            showNavigationLoader(destination);
        });
    }

    /* =====================================================
       2. RESPONSIVE NAVIGATION
       ===================================================== */

    const closeMenu = () => {
        if (!menu || !toggle || !menu.classList.contains('is-open')) {
            return;
        }

        menu.classList.remove('is-open');
        toggle.classList.remove('is-open');

        toggle.setAttribute('aria-expanded', 'false');
        body.classList.remove('menu-is-open');

        if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
            lastFocusedElement.focus();
        }
    };

    const openMenu = () => {
        if (!menu || !toggle) return;

        lastFocusedElement = document.activeElement;

        menu.classList.add('is-open');
        toggle.classList.add('is-open');

        toggle.setAttribute('aria-expanded', 'true');
        body.classList.add('menu-is-open');

        const firstLink = menu.querySelector('a');

        if (firstLink) {
            firstLink.focus();
        }
    };

    if (menu && toggle && header) {
        toggle.addEventListener('click', () => {
            if (menu.classList.contains('is-open')) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        document.addEventListener('pointerdown', (event) => {
            if (
                menu.classList.contains('is-open') &&
                !header.contains(event.target)
            ) {
                closeMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeMenu();
            }
        });

        menu.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                // Avoid unnecessary focus restoration after navigation.
                if (menu.classList.contains('is-open')) {
                    menu.classList.remove('is-open');
                    toggle.classList.remove('is-open');
                    toggle.setAttribute('aria-expanded', 'false');
                    body.classList.remove('menu-is-open');
                }
            });
        });
    }

    /* =====================================================
       3. HERO SLIDER
       ===================================================== */

    const hero = document.querySelector('[data-hero]');

    if (hero) {
        const slides = Array.from(
            hero.querySelectorAll('[data-hero-slide]')
        );

        const previousButton = hero.querySelector('[data-hero-previous]');
        const nextButton = hero.querySelector('[data-hero-next]');
        const pauseButton = hero.querySelector('[data-hero-pause]');
        const currentLabel = hero.querySelector('[data-hero-current]');

        const intervalDuration = 7500;

        let activeIndex = Math.max(
            0,
            slides.findIndex((slide) => slide.classList.contains('is-active'))
        );

        let timerId = null;
        let isPaused = reduceMotion;
        let touchStartX = null;

        const setSlideAccessibility = (slide, isActive) => {
            slide.setAttribute('aria-hidden', String(!isActive));

            slide.querySelectorAll('a').forEach((link) => {
                if (isActive) {
                    link.removeAttribute('tabindex');
                } else {
                    link.setAttribute('tabindex', '-1');
                }
            });
        };

        const stopAutoplay = () => {
            if (timerId !== null) {
                window.clearInterval(timerId);
            }

            timerId = null;
        };

        const startAutoplay = () => {
            stopAutoplay();

            if (!isPaused && !reduceMotion && slides.length > 1) {
                timerId = window.setInterval(() => {
                    showSlide(activeIndex + 1);
                }, intervalDuration);
            }
        };

        const showSlide = (nextIndex) => {
            if (!slides.length) return;

            const normalisedIndex =
                (nextIndex + slides.length) % slides.length;

            if (normalisedIndex === activeIndex) return;

            const previousSlide = slides[activeIndex];
            const nextSlide = slides[normalisedIndex];

            if (!previousSlide || !nextSlide) return;

            previousSlide.classList.remove('is-active');
            setSlideAccessibility(previousSlide, false);

            nextSlide.classList.add('is-active');
            setSlideAccessibility(nextSlide, true);

            activeIndex = normalisedIndex;

            if (currentLabel) {
                currentLabel.textContent = String(activeIndex + 1).padStart(
                    2,
                    '0'
                );
            }

            if (!reduceMotion && window.gsap) {
                window.gsap.fromTo(
                    nextSlide.querySelectorAll(
                        'h1, .eyebrow, .hero-slide__content > p:not(.eyebrow), .hero-slide__actions'
                    ),
                    {
                        y: 18,
                        opacity: 0
                    },
                    {
                        y: 0,
                        opacity: 1,
                        duration: 0.7,
                        stagger: 0.07,
                        ease: 'power3.out',
                        clearProps: 'transform,opacity'
                    }
                );
            }

            startAutoplay();
        };

        slides.forEach((slide, index) => {
            setSlideAccessibility(slide, index === activeIndex);
        });

        if (previousButton) {
            previousButton.addEventListener('click', () => {
                showSlide(activeIndex - 1);
            });
        }

        if (nextButton) {
            nextButton.addEventListener('click', () => {
                showSlide(activeIndex + 1);
            });
        }

        if (pauseButton) {
            pauseButton.addEventListener('click', () => {
                isPaused = !isPaused;

                pauseButton.setAttribute(
                    'aria-pressed',
                    String(isPaused)
                );

                pauseButton.textContent = isPaused
                    ? 'Resume motion'
                    : 'Pause motion';

                startAutoplay();
            });
        }

        hero.addEventListener('mouseenter', stopAutoplay);
        hero.addEventListener('mouseleave', startAutoplay);
        hero.addEventListener('focusin', stopAutoplay);

        hero.addEventListener('focusout', (event) => {
            if (!hero.contains(event.relatedTarget)) {
                startAutoplay();
            }
        });

        hero.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                showSlide(activeIndex - 1);
            }

            if (event.key === 'ArrowRight') {
                event.preventDefault();
                showSlide(activeIndex + 1);
            }
        });

        hero.addEventListener(
            'touchstart',
            (event) => {
                touchStartX = event.changedTouches[0].screenX;
            },
            { passive: true }
        );

        hero.addEventListener(
            'touchend',
            (event) => {
                if (touchStartX === null) return;

                const distance =
                    event.changedTouches[0].screenX - touchStartX;

                if (Math.abs(distance) > 48) {
                    showSlide(activeIndex + (distance < 0 ? 1 : -1));
                }

                touchStartX = null;
            },
            { passive: true }
        );

        startAutoplay();
    }

    /* =====================================================
       4. GSAP ANIMATIONS
       ===================================================== */

    if (!reduceMotion && window.gsap) {
        try {
            if (window.ScrollTrigger) {
                window.gsap.registerPlugin(window.ScrollTrigger);
            }

            window.gsap.from(
                '.hero-slide.is-active .hero-slide__content > *',
                {
                    delay: 0.2,
                    duration: 0.8,
                    y: 20,
                    opacity: 0,
                    stagger: 0.09,
                    ease: 'power3.out'
                }
            );

            if (window.ScrollTrigger) {
                document.querySelectorAll('[data-reveal]').forEach((element) => {
                    window.gsap.from(element, {
                        scrollTrigger: {
                            trigger: element,
                            start: 'top 86%',
                            once: true
                        },
                        duration: 0.7,
                        y: 20,
                        opacity: 0,
                        ease: 'power3.out'
                    });
                });
            }
        } catch (error) {
            // GSAP is progressive enhancement; its failure must not stop the site.
            root.classList.add('site-ready');
        }
    }

    /* =====================================================
       5. SITE READY
       ===================================================== */

    root.classList.add('site-ready');
})();
