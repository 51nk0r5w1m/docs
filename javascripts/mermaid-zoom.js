/* Mermaid diagram zoom — click any diagram to open fullscreen lightbox.
 * Works with Zensical/MkDocs Material which renders mermaid into closed
 * Shadow DOM, so we re-render from source on click using mermaid.render(). */
(function () {
  "use strict";

  var _uid = 0;

  function attachHandlers() {
    // Target the outer container elements that hold mermaid source.
    // Before rendering they are <pre class="mermaid">, after they become
    // <div class="mermaid"> with a closed shadow root containing the SVG.
    document.querySelectorAll(".mermaid").forEach(function (el) {
      if (el.dataset.zoomInit) return;
      el.dataset.zoomInit = "1";
      el.style.cursor = "zoom-in";
      el.title = "Click to zoom";
      el.addEventListener("click", function () {
        openLightbox(el);
      });
    });
  }

  function openLightbox(sourceEl) {
    // The diagram source text is stored in the element's textContent
    // (set before mermaid replaces it with a shadow root).
    var source = (sourceEl.dataset.mermaidSrc || sourceEl.textContent || "").trim();
    if (!source) return;

    var overlay = document.createElement("div");
    overlay.style.cssText = [
      "position:fixed", "inset:0", "z-index:9999",
      "background:rgba(0,0,0,0.82)",
      "display:flex", "align-items:center", "justify-content:center",
      "padding:24px", "box-sizing:border-box", "cursor:zoom-out"
    ].join(";");

    var card = document.createElement("div");
    card.style.cssText = [
      "background:#fff", "border-radius:8px", "padding:24px 20px 20px",
      "max-width:95vw", "max-height:92vh", "overflow:auto",
      "position:relative", "cursor:default",
      "box-shadow:0 8px 40px rgba(0,0,0,0.5)"
    ].join(";");

    var closeBtn = document.createElement("button");
    closeBtn.textContent = "\u2715";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.style.cssText = [
      "position:absolute", "top:8px", "right:12px",
      "background:none", "border:none", "font-size:20px",
      "cursor:pointer", "color:#555", "line-height:1", "padding:4px 8px"
    ].join(";");

    var diagramHolder = document.createElement("div");
    diagramHolder.style.cssText = "min-width:300px;min-height:100px;text-align:center";
    diagramHolder.textContent = "Rendering\u2026";

    card.appendChild(closeBtn);
    card.appendChild(diagramHolder);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    card.addEventListener("click", function (e) { e.stopPropagation(); });

    function close() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      document.removeEventListener("keydown", onKey);
    }
    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);
    function onKey(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", onKey);

    // Re-render the diagram using mermaid API
    if (window.mermaid && typeof mermaid.render === "function") {
      var id = "mermaid-zoom-" + (++_uid);
      Promise.resolve(mermaid.render(id, source)).then(function (result) {
        var svgStr = (result && result.svg) ? result.svg : result;
        diagramHolder.innerHTML = svgStr;
        var svg = diagramHolder.querySelector("svg");
        if (svg) {
          svg.removeAttribute("width");
          svg.removeAttribute("height");
          svg.style.maxWidth = "100%";
          svg.style.height = "auto";
        }
      }).catch(function () {
        diagramHolder.textContent = "Could not render diagram.";
      });
    } else {
      diagramHolder.textContent = "Mermaid not available.";
    }
  }

  // Capture source text before mermaid replaces it, then attach handlers.
  function captureAndAttach() {
    document.querySelectorAll(".mermaid:not([data-zoom-init])").forEach(function (el) {
      if (!el.dataset.mermaidSrc && el.textContent.trim()) {
        el.dataset.mermaidSrc = el.textContent.trim();
      }
    });
    attachHandlers();
  }

  // Poll until mermaid elements appear (they load async with the page)
  var _attempts = 0;
  function poll() {
    captureAndAttach();
    if (_attempts++ < 40) setTimeout(poll, 250);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", poll);
  } else {
    poll();
  }
})();
