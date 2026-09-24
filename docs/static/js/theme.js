(function () {
  "use strict";

  var storageKey = "avi-bench-theme";
  var root = document.documentElement;
  var themeQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var themeButton;
  var storedTheme = null;
  var hasManualPreference = false;

  try {
    storedTheme = window.localStorage.getItem(storageKey);
    hasManualPreference = storedTheme === "light" || storedTheme === "dark";
  } catch (error) {
    storedTheme = null;
  }

  function updateTheme(theme) {
    root.dataset.theme = theme;

    var themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) {
      themeColor.setAttribute("content", theme === "dark" ? "#0b1220" : "#f7faff");
    }

    if (themeButton) {
      var nextTheme = theme === "dark" ? "light" : "dark";
      var label = "Switch to " + nextTheme + " mode";
      themeButton.setAttribute("aria-label", label);
      themeButton.setAttribute("title", label);
    }
  }

  updateTheme(hasManualPreference ? storedTheme : (themeQuery.matches ? "dark" : "light"));

  function initializeThemeButton() {
    themeButton = document.getElementById("theme-toggle");
    if (!themeButton) {
      return;
    }

    updateTheme(root.dataset.theme);
    themeButton.addEventListener("click", function () {
      var theme = root.dataset.theme === "dark" ? "light" : "dark";
      hasManualPreference = true;
      updateTheme(theme);
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch (error) {
        // The active tab still switches themes if storage is unavailable.
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeThemeButton, { once: true });
  } else {
    initializeThemeButton();
  }

  function followSystemTheme(event) {
    if (!hasManualPreference) {
      updateTheme(event.matches ? "dark" : "light");
    }
  }

  if (typeof themeQuery.addEventListener === "function") {
    themeQuery.addEventListener("change", followSystemTheme);
  } else if (typeof themeQuery.addListener === "function") {
    themeQuery.addListener(followSystemTheme);
  }
}());
