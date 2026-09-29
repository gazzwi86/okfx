/* The OKFX bundle viewer. Reads BUNDLE and GRAPH, both inlined by graph.py. */
(function () {
  "use strict";

  var state = "raw";
  var activeTags = new Set();
  var selected = null;

  var byId = {};
  GRAPH.nodes.forEach(function (n) { byId[n.data.id] = n.data; });

  function view(id) {
    var node = byId[id];
    return node ? node[state] || node.raw : null;
  }

  function label(id) {
    var v = view(id);
    return (v && v.title) || id;
  }

  /* A bundle is untrusted input: its markdown must not be able to inject HTML
     into this page. Neutralising angle brackets before marked() sees them costs
     inline HTML (which OKF bodies have no need for) and nothing else. */
  function safeMarkdown(text) {
    var escaped = String(text || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return marked.parse(escaped, { breaks: false, mangle: false, headerIds: false });
  }

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---- graph ---------------------------------------------------------- */

  var cy = cytoscape({
    container: document.getElementById("graph"),
    elements: { nodes: GRAPH.nodes, edges: GRAPH.edges },
    minZoom: 0.15,
    maxZoom: 3,
    style: [
      {
        selector: "node",
        style: {
          "label": function (el) { return label(el.id()); },
          "font-size": 10,
          "color": "#888",
          "text-valign": "bottom",
          "text-margin-y": 5,
          "text-wrap": "ellipsis",
          "text-max-width": 130,
          "width": 18,
          "height": 18,
          "background-color": "#7e8ba3",
          "border-width": 2,
          "border-color": "#7e8ba3"
        }
      },
      { selector: 'node[?error]', style: { "border-color": "#b3261e", "border-style": "dashed" } },
      { selector: "node:selected", style: { "border-color": "#1f6feb", "width": 24, "height": 24 } },
      { selector: "node.dim", style: { "opacity": 0.12 } },
      {
        selector: "edge",
        style: {
          "width": 1.4,
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.8
        }
      },
      {
        selector: 'edge[kind = "extends"]',
        style: { "line-color": "#1f6feb", "target-arrow-color": "#1f6feb", "width": 2 }
      },
      {
        selector: 'edge[kind = "source"]',
        style: { "line-color": "#9a6700", "target-arrow-color": "#9a6700", "line-style": "dashed" }
      },
      {
        selector: 'edge[kind = "link"]',
        style: { "line-color": "#8b8b85", "target-arrow-color": "#8b8b85", "line-style": "dotted" }
      },
      { selector: "edge.hidden", style: { "display": "none" } },
      { selector: "edge.dim", style: { "opacity": 0.08 } }
    ]
  });

  var layouts = {
    cose: { name: "cose", animate: false, padding: 40, nodeRepulsion: 9000, idealEdgeLength: 90 },
    breadthfirst: { name: "breadthfirst", animate: false, padding: 40, spacingFactor: 1.2 },
    concentric: { name: "concentric", animate: false, padding: 40 },
    grid: { name: "grid", animate: false, padding: 40 }
  };

  function runLayout(name) {
    cy.layout(layouts[name] || layouts.cose).run();
  }

  /* ---- filtering ------------------------------------------------------ */

  function matches(id) {
    var v = view(id);
    if (!v) return false;
    var term = document.getElementById("search").value.trim().toLowerCase();
    var type = document.getElementById("type-filter").value;
    if (type && v.type !== type) return false;
    if (activeTags.size) {
      var hasAll = true;
      activeTags.forEach(function (t) { if (v.tags.indexOf(t) === -1) hasAll = false; });
      if (!hasAll) return false;
    }
    if (!term) return true;
    var haystack = [id, v.title, v.description, v.body].concat(v.tags).join(" ").toLowerCase();
    return haystack.indexOf(term) !== -1;
  }

  function apply() {
    var visibleKinds = {
      extends: document.getElementById("show-extends").checked,
      source: document.getElementById("show-source").checked,
      link: document.getElementById("show-link").checked
    };
    var shown = 0;
    cy.nodes().forEach(function (node) {
      var ok = matches(node.id());
      node.toggleClass("dim", !ok);
      if (ok) shown++;
    });
    cy.edges().forEach(function (edge) {
      var kind = edge.data("kind");
      edge.toggleClass("hidden", !visibleKinds[kind]);
      edge.toggleClass("dim", edge.source().hasClass("dim") || edge.target().hasClass("dim"));
    });
    cy.style().update();
    document.getElementById("stats").textContent =
      shown + " of " + cy.nodes().length + " concepts, " + cy.edges().length + " edges";
    // Deliberately not redrawing the detail panel: filtering cannot change the
    // selected concept's own content, and rebuilding it per keystroke re-parses
    // its markdown and throws away the reader's scroll position.
  }

  /* ---- detail panel --------------------------------------------------- */

  function badges(v, node) {
    var wrap = element("div", "badges");
    wrap.appendChild(element("span", "badge", v.type));
    if (v.status) wrap.appendChild(element("span", "badge", v.status));
    wrap.appendChild(element("span", "badge " + v.trust_tier, v.trust_tier.replace(/-/g, " ")));
    if (v.sealed) wrap.appendChild(element("span", "badge sealed", "sealed"));
    if (v.stale_after && new Date(v.stale_after) <= new Date()) {
      wrap.appendChild(element("span", "badge stale", "stale"));
    }
    if (node.error) wrap.appendChild(element("span", "badge error", "does not resolve"));
    return wrap;
  }

  /* Resolve a markdown link to a concept id, by the same rule graph.py uses:
     a leading slash means from the bundle root, anything else is relative to the
     linking document's own directory. Getting this wrong does not error, it
     quietly opens the wrong concept, so the two implementations have to agree. */
  function linkTarget(href, fromId) {
    var path = href.replace(/#.*$/, "").replace(/\.md$/, "");
    if (!path) return null;
    var segments;
    if (path.charAt(0) === "/") {
      segments = path.slice(1).split("/");
    } else {
      segments = fromId.split("/").slice(0, -1).concat(path.split("/"));
    }
    var stack = [];
    segments.forEach(function (segment) {
      if (segment === "" || segment === ".") return;
      if (segment === "..") { stack.pop(); return; }
      stack.push(segment);
    });
    var id = stack.join("/");
    return byId[id] ? id : null;
  }

  function section(heading) {
    var s = element("section");
    s.appendChild(element("h3", null, heading));
    return s;
  }

  function conceptLinks(ids, listClass) {
    var list = element("ul", listClass || null);
    ids.forEach(function (raw) {
      var id = raw.replace(/^\//, "").replace(/\.md$/, "");
      var item = element("li");
      if (byId[id]) {
        var a = element("a", null, label(id));
        a.href = "#" + id;
        a.addEventListener("click", function (event) {
          event.preventDefault();
          select(id);
        });
        item.appendChild(a);
      } else {
        item.appendChild(element("code", null, raw));
      }
      list.appendChild(item);
    });
    return list;
  }

  function showDetail(id) {
    var node = byId[id];
    var v = view(id);
    if (!node || !v) return;
    var panel = document.getElementById("detail-body");
    panel.textContent = "";

    var title = element("h2", null, v.title || id);
    panel.appendChild(title);
    panel.appendChild(element("div", "id", id));
    panel.appendChild(badges(v, node));
    if (v.description) panel.appendChild(element("p", null, v.description));
    if (node.error) {
      var err = section("Problem");
      err.appendChild(element("p", "error", node.error));
      panel.appendChild(err);
    }

    if (v.tags.length) {
      var tagSection = section("Tags");
      tagSection.appendChild(element("p", null, v.tags.join(", ")));
      panel.appendChild(tagSection);
    }

    var incoming = cy.getElementById(id).incomers('edge[kind = "extends"]');
    var extendsEdges = cy.getElementById(id).outgoers('edge[kind = "extends"]');
    if (extendsEdges.length) {
      var baseSection = section(state === "resolved" ? "Resolved from" : "Extends");
      var chain = state === "resolved" && v.resolved_from.length
        ? v.resolved_from
        : extendsEdges.map(function (e) { return e.target().id(); });
      baseSection.appendChild(conceptLinks(chain, "chain"));
      panel.appendChild(baseSection);
    }
    if (incoming.length) {
      var derived = section("Derived from this");
      derived.appendChild(conceptLinks(incoming.map(function (e) { return e.source().id(); })));
      panel.appendChild(derived);
    }
    if (v.validation.length) {
      var checks = section("Declared validators");
      checks.appendChild(conceptLinks(v.validation));
      panel.appendChild(checks);
    }

    var bodySection = section(state === "resolved" ? "Body, merged" : "Body, as written");
    var rendered = element("div");
    rendered.innerHTML = safeMarkdown(v.body);
    rendered.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (/^[a-z]+:/i.test(href)) {
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        return;
      }
      var resolvedId = linkTarget(href, id);
      if (resolvedId) {
        a.addEventListener("click", function (event) {
          event.preventDefault();
          select(resolvedId);
        });
      } else {
        a.removeAttribute("href");
      }
    });
    bodySection.appendChild(rendered);
    panel.appendChild(bodySection);

    document.getElementById("detail").hidden = false;
  }

  function select(id) {
    selected = id;
    cy.$(":selected").unselect();
    var node = cy.getElementById(id);
    if (node.length) node.select();
    showDetail(id);
    // A concept in the address bar makes a view shareable, and is how a reader
    // arriving from a link lands on the concept the link meant.
    if (window.location.hash.slice(1) !== id) {
      window.history.replaceState(null, "", "#" + id);
    }
  }

  /* ---- wiring --------------------------------------------------------- */

  document.getElementById("bundle-name").textContent = BUNDLE;

  var typeFilter = document.getElementById("type-filter");
  GRAPH.types.forEach(function (t) {
    var option = element("option", null, t);
    option.value = t;
    typeFilter.appendChild(option);
  });

  var tagBar = document.getElementById("tags");
  GRAPH.tags.forEach(function (t) {
    var chip = element("button", "tag", t);
    chip.type = "button";
    chip.setAttribute("aria-pressed", "false");
    chip.addEventListener("click", function () {
      if (activeTags.has(t)) { activeTags.delete(t); } else { activeTags.add(t); }
      chip.setAttribute("aria-pressed", activeTags.has(t) ? "true" : "false");
      apply();
    });
    tagBar.appendChild(chip);
  });

  document.getElementById("search").addEventListener("input", apply);
  typeFilter.addEventListener("change", apply);
  ["show-extends", "show-source", "show-link"].forEach(function (elementId) {
    document.getElementById(elementId).addEventListener("change", apply);
  });
  document.getElementById("layout").addEventListener("change", function (event) {
    runLayout(event.target.value);
  });
  document.querySelectorAll('input[name="state"]').forEach(function (radio) {
    radio.addEventListener("change", function () {
      state = radio.value;
      cy.style().update();
      apply();
      if (selected) showDetail(selected);
    });
  });
  document.getElementById("reset").addEventListener("click", function () {
    document.getElementById("search").value = "";
    typeFilter.value = "";
    activeTags.clear();
    tagBar.querySelectorAll(".tag").forEach(function (chip) {
      chip.setAttribute("aria-pressed", "false");
    });
    selected = null;
    document.getElementById("detail").hidden = true;
    cy.$(":selected").unselect();
    apply();
    cy.fit(undefined, 40);
  });
  document.getElementById("close-detail").addEventListener("click", function () {
    selected = null;
    document.getElementById("detail").hidden = true;
    cy.$(":selected").unselect();
  });

  cy.on("tap", "node", function (event) { select(event.target.id()); });
  cy.on("tap", function (event) {
    if (event.target === cy) {
      selected = null;
      document.getElementById("detail").hidden = true;
    }
  });

  window.addEventListener("hashchange", function () {
    var id = decodeURIComponent(window.location.hash.slice(1));
    if (id && byId[id] && id !== selected) select(id);
  });

  runLayout("cose");
  apply();

  var initial = decodeURIComponent(window.location.hash.slice(1));
  if (initial && byId[initial]) select(initial);
})();
