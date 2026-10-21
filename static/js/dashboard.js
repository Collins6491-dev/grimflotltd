/* Dashboard navigation: responsive sidebar and accessible mobile drawer. */
(() => {
    const sidebar = document.querySelector("[data-dashboard-sidebar]");
    const toggle = document.querySelector("[data-dashboard-toggle]");
    const backdrop = document.querySelector("[data-dashboard-backdrop]");
    const toggleLabel = toggle?.querySelector("[data-dashboard-toggle-label]");

    if (!sidebar || !toggle || !backdrop) return;

    const mobileQuery = window.matchMedia("(max-width: 900px)");

    const isOpen = () => sidebar.classList.contains("is-open");

    const open = () => {
        if (!mobileQuery.matches) return;

        sidebar.classList.add("is-open");
        backdrop.hidden = false;
        document.body.classList.add("dashboard-drawer-open");

        toggle.setAttribute("aria-expanded", "true");
        toggle.setAttribute("aria-label", "Close operations navigation");

        if (toggleLabel) {
            toggleLabel.textContent = "Close operations navigation";
        }

        const firstLink = sidebar.querySelector("nav a");

        if (firstLink) {
            firstLink.focus({ preventScroll: true });
        }
    };

    const close = ({ restoreFocus = false } = {}) => {
        sidebar.classList.remove("is-open");
        backdrop.hidden = true;
        document.body.classList.remove("dashboard-drawer-open");

        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open operations navigation");

        if (toggleLabel) {
            toggleLabel.textContent = "Open operations navigation";
        }

        if (restoreFocus && mobileQuery.matches) {
            toggle.focus({ preventScroll: true });
        }
    };

    /* Highlight the current dashboard page. */
    sidebar.querySelectorAll("nav a").forEach((link) => {
        if (link.pathname === window.location.pathname) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });

    /* Hamburger and X button. */
    toggle.addEventListener("click", () => {
        if (isOpen()) {
            close({ restoreFocus: true });
        } else {
            open();
        }
    });

    /* Close the drawer when the backdrop is clicked. */
    backdrop.addEventListener("click", () => {
        close({ restoreFocus: true });
    });

    /* Close the drawer when a navigation link is selected. */
    sidebar.querySelectorAll("nav a").forEach((link) => {
        link.addEventListener("click", () => {
            close();
        });
    });

    /* Close the drawer using Escape. */
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && isOpen()) {
            close({ restoreFocus: true });
        }
    });

    /* Keep the drawer and body state consistent across breakpoints. */
    const handleBreakpointChange = () => {
        if (!mobileQuery.matches) {
            close();
        }
    };

    if (mobileQuery.addEventListener) {
        mobileQuery.addEventListener("change", handleBreakpointChange);
    } else {
        mobileQuery.addListener(handleBreakpointChange);
    }

    /* Initialize the drawer in a closed state. */
    close();
})();