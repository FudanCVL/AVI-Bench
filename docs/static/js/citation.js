(function () {
  "use strict";

  var button = document.getElementById("copy-citation");
  var citation = document.getElementById("citation-bibtex");
  var status = document.getElementById("citation-copy-status");
  var statusTimer;

  if (!button || !citation || !status) {
    return;
  }

  function announce(message, isError) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
    window.clearTimeout(statusTimer);
    statusTimer = window.setTimeout(function () {
      status.textContent = "";
      status.classList.remove("is-error");
    }, 3000);
  }

  function fallbackCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);

    try {
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);
      return typeof document.execCommand === "function" && document.execCommand("copy");
    } catch (error) {
      return false;
    } finally {
      textarea.remove();
    }
  }

  button.addEventListener("click", async function () {
    var text = citation.textContent.trim();

    var copied = false;

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        copied = true;
      }
    } catch (error) {
      copied = false;
    }

    if (!copied) {
      copied = fallbackCopy(text);
    }

    announce(copied ? "Copied!" : "Copy failed. Select the BibTeX text to copy.", !copied);
  });
}());
