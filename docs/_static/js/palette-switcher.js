// Live palette + code-theme switcher for the Furo theme.
//
// The PALETTES and CODE_THEMES registries are injected by conf.py, so this script has
// no colors of its own. It overrides Furo's brand/background CSS variables to switch the
// site palette, and tags <body> to select one of the pre-rendered Pygments themes (see
// css/pygments-themes.css):
//   * data-code-theme — an explicit pick from the dropdown; applies in light AND dark.
//   * data-code-auto  — the palette's dark default ("Auto"); applies in dark mode only.
// Both choices persist in localStorage and compose with Furo's light/dark/auto toggle.
(function () {
  "use strict";

  var PALETTES = window.DOCS_PALETTES || {};
  var PALETTE_DEFAULT = window.DOCS_PALETTE_DEFAULT;
  var CODE_THEMES = window.DOCS_CODE_THEMES || {}; // { groupLabel: [styleName, …] }
  var SHOW_SWITCHER = !!window.DOCS_SHOW_SWITCHER; // render the dropdowns, or just paint
  var PALETTE_KEY = "docs-palette";
  var CODE_KEY = "docs-code-theme";

  var paletteNames = Object.keys(PALETTES);
  var codeMenu = []; // flattened list of every selectable style, for validation
  Object.keys(CODE_THEMES).forEach(function (group) {
    codeMenu = codeMenu.concat(CODE_THEMES[group]);
  });
  if (!paletteNames.length) return; // nothing to paint

  // ---- palette: override Furo's brand/background variables ----

  // Turn a {furo-css-var: value} dict into CSS declarations.
  function declarations(obj) {
    return Object.keys(obj)
      .map(function (key) {
        return "--" + key.replace(/^--/, "") + ":" + obj[key] + ";";
      })
      .join("");
  }

  // Mirror how Furo applies light/dark variables, so the switcher composes with Furo's
  // own light/dark/auto toggle.
  function applyPalette(name) {
    var p = PALETTES[name];
    if (!p) return;
    var light = declarations(p.light);
    var dark = declarations(p.dark);
    var css =
      'body, body[data-theme="light"] {' +
      light +
      "}" +
      'body[data-theme="dark"] {' +
      dark +
      "}" +
      '@media (prefers-color-scheme: dark){body[data-theme="auto"]{' +
      dark +
      "}}" +
      '@media (prefers-color-scheme: light){body[data-theme="auto"]{' +
      light +
      "}}";
    setStyle("docs-palette-override", css);
    applyCode(name); // the palette's "Auto" default may have changed
  }

  // ---- code theme: tag <body> to pick a pre-rendered Pygments theme ----

  // An explicit dropdown pick (data-code-theme) wins and applies in both modes. With no
  // pick, the palette's per-mode defaults ride on data-code-auto (dark) and
  // data-code-auto-light (light), each scoped to its own mode; a mode with no default
  // keeps Furo's global Pygments style.
  function applyCode(paletteName) {
    var override = storedCode();
    var p = PALETTES[paletteName] || {};
    withBody(function () {
      var body = document.body;
      if (override) {
        body.setAttribute("data-code-theme", override);
        body.removeAttribute("data-code-auto");
        body.removeAttribute("data-code-auto-light");
      } else {
        body.removeAttribute("data-code-theme");
        toggleAttr(body, "data-code-auto", p.dark_pygments);
        toggleAttr(body, "data-code-auto-light", p.light_pygments);
      }
    });
  }

  function toggleAttr(el, name, value) {
    if (value) el.setAttribute(name, value);
    else el.removeAttribute(name);
  }

  // ---- storage + small helpers ----

  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }
  function write(key, value) {
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch (e) {}
  }

  // When the dropdowns are hidden (published/locked build) we ignore any saved choices
  // and always show the configured defaults, so a stale localStorage value can't override
  // the served look. localStorage is only consulted when the controls are available.
  function currentPalette() {
    var saved = SHOW_SWITCHER && read(PALETTE_KEY);
    if (saved && PALETTES[saved]) return saved;
    return PALETTES[PALETTE_DEFAULT] ? PALETTE_DEFAULT : paletteNames[0];
  }
  function storedCode() {
    if (!SHOW_SWITCHER) return "";
    var saved = read(CODE_KEY);
    return saved && codeMenu.indexOf(saved) >= 0 ? saved : "";
  }

  // applyPalette/applyCode can run before parsing finishes; defer <body> writes.
  function withBody(fn) {
    if (document.body) fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function setStyle(id, css) {
    var style = document.getElementById(id);
    if (!style) {
      style = document.createElement("style");
      style.id = id;
      (document.head || document.documentElement).appendChild(style);
    }
    style.textContent = css;
  }

  function option(value, text, selected) {
    var el = document.createElement("option");
    el.value = value;
    el.textContent = text;
    if (value === selected) el.selected = true;
    return el;
  }

  // ---- UI ----

  // Build a switcher pill: an icon plus a <select> populated by `fill(select)`.
  function makeControl(icon, ariaLabel, fill, onChange) {
    var wrap = document.createElement("div");
    wrap.className = "palette-switcher";

    var label = document.createElement("span");
    label.className = "palette-switcher__icon";
    label.textContent = icon;
    label.setAttribute("aria-hidden", "true");

    var select = document.createElement("select");
    select.setAttribute("aria-label", ariaLabel);
    fill(select);
    select.addEventListener("change", function () {
      onChange(select.value);
    });

    wrap.appendChild(label);
    wrap.appendChild(select);
    return wrap;
  }

  function buildControls(paletteName) {
    var bar = document.createElement("div");
    bar.className = "palette-switcher-bar";

    if (paletteNames.length >= 2) {
      bar.appendChild(
        makeControl(
          "🎨",
          "Color palette",
          function (select) {
            paletteNames.forEach(function (n) {
              select.appendChild(option(n, n, paletteName));
            });
          },
          function (value) {
            applyPalette(value);
            write(PALETTE_KEY, value);
          },
        ),
      );
    }

    if (codeMenu.length >= 1) {
      var selectedCode = storedCode();
      bar.appendChild(
        makeControl(
          "</>",
          "Code theme",
          function (select) {
            select.appendChild(option("", "Auto", selectedCode)); // "" = follow palette
            Object.keys(CODE_THEMES).forEach(function (group) {
              var og = document.createElement("optgroup");
              og.label = group;
              CODE_THEMES[group].forEach(function (style) {
                og.appendChild(option(style, style, selectedCode));
              });
              select.appendChild(og);
            });
          },
          function (value) {
            write(CODE_KEY, value);
            applyCode(currentPalette());
          },
        ),
      );
    }

    document.body.appendChild(bar);
  }

  // ---- init ----

  var name = currentPalette();
  applyPalette(name); // always paint the palette + default code themes; early to limit flash

  if (!SHOW_SWITCHER) return; // published build: locked to the active palette, no controls

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      buildControls(name);
    });
  } else {
    buildControls(name);
  }
})();
