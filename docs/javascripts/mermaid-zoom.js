/* Mermaid diagram zoom — click any rendered diagram to open fullscreen lightbox.
 *
 * How Zensical/MkDocs renders mermaid:
 *  1. HTML has <pre class="mermaid"><code>source</code></pre>
 *  2. Bundle JS removes "mermaid" class from <pre>, reads textContent as source
 *  3. Creates a new <div class="mermaid"> with a CLOSED shadow root containing the SVG
 *  4. Replaces the <pre> with the <div>
 *
 * Strategy: capture sources from <pre class="mermaid"> elements synchronously
 * before mermaid processes them, then attach click handlers to the replacement
 * <div class="mermaid"> elements via MutationObserver.
 */
(function () {
  "use strict";

  // Queue of diagram sources captured from <pre class="mermaid"> elements
  var sourceQueue = [];
  var _uid = 0;

  function captureSources() {
    document.querySelectorAll("pre.mermaid").forEach(function (pre) {
      if (!pre.dataset.zoomCaptured) {
        pre.dataset.zoomCaptured = "1";
        sourceQueue.push(pre.textContent.trim());
      }
    });
  }

  function attachToDiv(div) {
    if (div.dataset.zoomInit) return;
    div.dataset.zoomInit = "1";
    // Assign source from queue (mermaid processes in DOM order)
    if (!div.dataset.mermaidSrc && sourceQueue.length > 0) {
      div.dataset.mermaidSrc = sourceQueue.shift();
    }
    if (!div.dataset.mermaidSrc) return;
    div.style.cursor = "zoom-in";
    div.title = "Click to zoom";
    div.addEventListener("click", function () {
      openLightbox(div.dataset.mermaidSrc);
    });
  }

  function openLightbox(source) {
    if (!source) return;

    var overlay = document.createElement("div");
    overlay.style.cssText = [
      "position:fixed","inset:0","z-index:9999",
      "background:rgba(0,0,0,0.82)",
      "display:flex","align-items:center","justify-content:center",
      "padding:24px","box-sizing:border-box","cursor:zoom-out"
    ].join(";");

    var card = document.createElement("div");
    card.style.cssText = [
      "background:#fff","border-radius:8px","padding:24px 20px 20px",
      "max-width:95vw","max-height:92vh","overflow:auto",
      "position:relative","cursor:default",
      "box-shadow:0 8px 40px rgba(0,0,0,0.5)"
    ].join(";");

    var closeBtn = document.createElement("button");
    closeBtn.textContent = "\u2715";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.style.cssText = [
      "position:absolute","top:8px","right:12px",
      "background:none","border:none","font-size:20px",
      "cursor:pointer","color:#555","line-height:1","padding:4px 8px"
    ].join(";");

    var holder = document.createElement("div");
    holder.style.cssText = "min-width:320px;min-height:80px;text-align:center";
    holder.textContent = "Rendering\u2026";

    card.appendChild(closeBtn);
    card.appendChild(holder);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    card.addEventListener("click", function (e) { e.stopPropagation(); });

    function close() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      document.removeEventListener("keydown", onKey);
    }
    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", function (e) { e.stopPropagation(); close(); });
    function onKey(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", onKey);

    if (window.mermaid && typeof mermaid.render === "function") {
      var id = "mz" + (++_uid);
      Promise.resolve(mermaid.render(id, source)).then(function (result) {
        var svgStr = (result && result.svg) ? result.svg : String(result);
        holder.innerHTML = svgStr;
        var svg = holder.querySelector("svg");
        if (svg) {
          svg.removeAttribute("width");
          svg.removeAttribute("height");
          svg.style.cssText = "max-width:100%;height:auto;display:block;margin:0 auto";
        }
      }).catch(function (err) {
        holder.textContent = "Could not render diagram.";
      });
    } else {
      holder.textContent = "Mermaid unavailable.";
    }
  }

  // Watch for <div class="mermaid"> elements being inserted by the mermaid bundle
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (node) {
        if (node.nodeType === 1 && node.tagName === "DIV" && node.classList.contains("mermaid")) {
          attachToDiv(node);
        }
      });
    });
  });

  function init() {
    // 1. Capture all pre.mermaid sources before mermaid processes them
    captureSources();
    // 2. Attach to any <div class="mermaid"> already in the DOM
    document.querySelectorAll("div.mermaid").forEach(attachToDiv);
    // 3. Watch for future insertions
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
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
