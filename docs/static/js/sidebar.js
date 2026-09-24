(function () {
  "use strict";

  var panel = document.getElementById("page-sidebar");
  var toggle = document.getElementById("side-rail-toggle");
  var backdrop = document.getElementById("side-rail-backdrop");
  var desktopQuery = window.matchMedia("(min-width: 1680px)");

  function isOpen() {
    return panel.classList.contains("is-open");
  }

  function syncState() {
    var desktop = desktopQuery.matches;
    var open = !desktop && isOpen();

    toggle.hidden = desktop;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close page contents" : "Open page contents");
    backdrop.hidden = !open;
    panel.setAttribute("aria-hidden", String(!desktop && !open));
    panel.inert = !desktop && !open;
    document.body.classList.toggle("side-rail-open", open);
  }

  function closePanel(restoreFocus) {
    panel.classList.remove("is-open");
    syncState();
    if (restoreFocus) {
      toggle.focus({ preventScroll: true });
    }
  }

  function focusFirstLink() {
    var firstLink = panel.querySelector(".side-rail-nav a");
    if (firstLink) {
      firstLink.focus({ preventScroll: true });
    }
  }

  toggle.addEventListener("click", function () {
    if (desktopQuery.matches) {
      return;
    }
    if (isOpen()) {
      closePanel(false);
      return;
    }

    panel.classList.add("is-open");
    syncState();
    focusFirstLink();
  });

  backdrop.addEventListener("click", function () {
    closePanel(true);
  });

  panel.addEventListener("click", function (event) {
    var link = event.target.closest(".side-rail-nav a[href^='#']");
    if (!link) {
      return;
    }

    var target = document.getElementById(link.getAttribute("href").slice(1));
    if (!target) {
      return;
    }

    event.preventDefault();
    if (!desktopQuery.matches) {
      closePanel(false);
    }
    window.history.pushState(null, "", link.getAttribute("href"));
    target.focus({ preventScroll: true });
    target.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start"
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isOpen()) {
      closePanel(true);
    }
  });

  if (typeof desktopQuery.addEventListener === "function") {
    desktopQuery.addEventListener("change", function () {
      var focusWasInPanel = panel.contains(document.activeElement);
      var focusWasOnToggle = document.activeElement === toggle;
      panel.classList.remove("is-open");
      syncState();
      if (desktopQuery.matches && focusWasOnToggle) {
        focusFirstLink();
      } else if (!desktopQuery.matches && focusWasInPanel) {
        toggle.focus({ preventScroll: true });
      }
    });
  } else {
    desktopQuery.addListener(function () {
      var focusWasInPanel = panel.contains(document.activeElement);
      var focusWasOnToggle = document.activeElement === toggle;
      panel.classList.remove("is-open");
      syncState();
      if (desktopQuery.matches && focusWasOnToggle) {
        focusFirstLink();
      } else if (!desktopQuery.matches && focusWasInPanel) {
        toggle.focus({ preventScroll: true });
      }
    });
  }

  syncState();
})();
