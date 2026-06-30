// Progressive-enhancement layer for the Hermes Company OS dashboard.
// hx-boost (set on <body>) turns same-origin links and form posts into
// AJAX body-swaps, removing the full-page-reload flash. This script:
//   1. re-renders lucide icons after each swap (boosted content is new DOM),
//   2. drives a thin top progress bar during htmx requests.
// Everything degrades gracefully: with JS off, links/forms work as normal.
(function () {
  "use strict";

  function renderIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function progressBar() {
    return document.getElementById("app-progress");
  }

  // Query fresh each time: hx-boost swaps <body> innerHTML, so a cached
  // reference would go stale after the first navigation.
  function showProgress() {
    window.__appReq = (window.__appReq || 0) + 1;
    var bar = progressBar();
    if (bar) bar.classList.add("is-active");
  }
  function hideProgress() {
    window.__appReq = Math.max(0, (window.__appReq || 0) - 1);
    if (window.__appReq === 0) {
      var bar = progressBar();
      if (bar) bar.classList.remove("is-active");
    }
  }

  // hx-boost catches every same-origin link, but export links point at raw
  // documents (.md/.json/.ps1/…). Boosting those would swap plain text into
  // the page body — so let the browser handle them natively instead.
  var DOC_LINK = /\.(md|json|csv|txt|ya?ml|ps1|zip|pdf)$/i;
  document.body.addEventListener("htmx:beforeRequest", function (evt) {
    var cfg = evt.detail && evt.detail.requestConfig;
    if (!cfg || (cfg.verb && cfg.verb !== "get")) return;
    var path = cfg.path || "";
    if (DOC_LINK.test(path.split("?")[0])) {
      evt.preventDefault();
      window.location.href = path;
    }
  });

  document.addEventListener("DOMContentLoaded", renderIcons);
  document.body.addEventListener("htmx:load", renderIcons);
  document.body.addEventListener("htmx:afterSwap", renderIcons);

  document.body.addEventListener("htmx:beforeRequest", showProgress);
  document.body.addEventListener("htmx:afterRequest", hideProgress);
  document.body.addEventListener("htmx:responseError", hideProgress);
  document.body.addEventListener("htmx:sendError", hideProgress);
})();
