/* Mermaid diagram zoom — click any diagram to open fullscreen with pan/zoom */
(function () {
  "use strict";

  function initZoom() {
    document.querySelectorAll(".mermaid svg").forEach(function (svg) {
      if (svg.dataset.zoomInit) return;
      svg.dataset.zoomInit = "1";

      // Make the SVG visually indicate it's clickable
      svg.style.cursor = "zoom-in";
      svg.setAttribute("title", "Click to zoom");

      svg.addEventListener("click", function () {
        openLightbox(svg);
      });
    });
  }

  function openLightbox(originalSvg) {
    // Clone SVG so we don't mutate the original
    var clone = originalSvg.cloneNode(true);
    clone.removeAttribute("width");
    clone.removeAttribute("height");
    clone.style.cursor = "default";
    clone.style.maxWidth = "100%";
    clone.style.maxHeight = "100%";

    // Overlay
    var overlay = document.createElement("div");
    overlay.id = "mermaid-zoom-overlay";
    overlay.style.cssText = [
      "position:fixed", "inset:0", "z-index:9999",
      "background:rgba(0,0,0,0.82)",
      "display:flex", "align-items:center", "justify-content:center",
      "padding:24px", "box-sizing:border-box",
      "cursor:zoom-out"
    ].join(";");

    // Inner container (white card)
    var card = document.createElement("div");
    card.style.cssText = [
      "background:#fff", "border-radius:8px",
      "padding:16px", "max-width:95vw", "max-height:92vh",
      "overflow:auto", "position:relative",
      "cursor:default", "box-shadow:0 8px 40px rgba(0,0,0,0.5)"
    ].join(";");

    // Close button
    var closeBtn = document.createElement("button");
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = [
      "position:absolute", "top:8px", "right:12px",
      "background:none", "border:none", "font-size:20px",
      "cursor:pointer", "color:#555", "line-height:1", "padding:4px 8px"
    ].join(";");
    closeBtn.setAttribute("aria-label", "Close");

    card.appendChild(closeBtn);
    card.appendChild(clone);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    // Prevent card clicks from closing overlay
    card.addEventListener("click", function (e) { e.stopPropagation(); });

    function close() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      document.removeEventListener("keydown", onKey);
    }

    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);

    function onKey(e) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
  }

  // Run after mermaid renders (it renders asynchronously)
  function observe() {
    var observer = new MutationObserver(function () {
      initZoom();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Also run immediately in case diagrams already rendered
    initZoom();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observe);
  } else {
    observe();
  }
})();
