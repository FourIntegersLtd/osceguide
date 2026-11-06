/*
 * A small stand-in for the design boards' own runtime (./support.js), which is not in the
 * repository. It renders the <x-dc> template the way a board needs: {{ expr }} in text and
 * attributes, <sc-for list as>, <sc-if value>, onClick={{ fn }}, and the board's DCLogic class
 * (state, setState, renderVals). Served as /support.js by e2e/support/board-diff.ts.
 */
(function () {
  class DCLogic {
    constructor(props) {
      this.props = props || {};
      this.state = {};
      this.__render = null;
    }
    setState(patch) {
      this.state = Object.assign({}, this.state, typeof patch === "function" ? patch(this.state) : patch);
      if (this.__render) this.__render();
    }
  }
  window.DCLogic = DCLogic;

  const evaluate = (expr, scope) => {
    const keys = Object.keys(scope);
    return new Function(...keys, "return (" + expr + ");")(...keys.map((k) => scope[k]));
  };
  const WHOLE = /^\s*\{\{([\s\S]*)\}\}\s*$/;
  const interpolate = (text, scope) =>
    text.replace(/\{\{([\s\S]*?)\}\}/g, (_, expr) => {
      const v = evaluate(expr, scope);
      return v === undefined || v === null || v === false ? "" : String(v);
    });

  function renderChildren(parent, scope) {
    for (const node of Array.from(parent.childNodes)) renderNode(node, scope);
  }

  function renderNode(node, scope) {
    if (node.nodeType === 3) {
      if (node.nodeValue.includes("{{")) node.nodeValue = interpolate(node.nodeValue, scope);
      return;
    }
    if (node.nodeType !== 1) return;
    const tag = node.tagName.toLowerCase();
    if (tag === "sc-for") {
      const list = evaluate(WHOLE.exec(node.getAttribute("list"))[1], scope) || [];
      const as = node.getAttribute("as") || "item";
      const frag = document.createDocumentFragment();
      list.forEach((item, index) => {
        const copy = node.cloneNode(true);
        renderChildren(copy, Object.assign({}, scope, { [as]: item, index }));
        while (copy.firstChild) frag.appendChild(copy.firstChild);
      });
      node.replaceWith(frag);
      return;
    }
    if (tag === "sc-if") {
      const show = evaluate(WHOLE.exec(node.getAttribute("value"))[1], scope);
      if (!show) return void node.remove();
      renderChildren(node, scope);
      node.replaceWith(...Array.from(node.childNodes));
      return;
    }
    for (const attr of Array.from(node.attributes)) {
      if (!attr.value.includes("{{")) continue;
      if (/^on/i.test(attr.name)) {
        const fn = evaluate(WHOLE.exec(attr.value)[1], scope);
        node.removeAttribute(attr.name);
        if (typeof fn === "function") node.addEventListener(attr.name.slice(2).toLowerCase(), fn);
      } else {
        node.setAttribute(attr.name, interpolate(attr.value, scope));
      }
    }
    renderChildren(node, scope);
  }

  function boot() {
    const root = document.querySelector("x-dc");
    const script = document.querySelector("script[data-dc-script]");
    if (!root || !script) return;
    const template = root.innerHTML;
    const props = JSON.parse(script.getAttribute("data-props") || "{}");
    const Component = new Function("DCLogic", script.textContent + "\n;return Component;")(DCLogic);
    const logic = new Component(props);
    const draw = () => {
      const holder = document.createElement("div");
      holder.innerHTML = template;
      renderChildren(holder, logic.renderVals ? logic.renderVals() : {});
      root.replaceChildren(...Array.from(holder.childNodes));
      document.body.dataset.dcReady = "1";
    };
    logic.__render = draw;
    draw();
  }

  const style = document.createElement("style");
  style.textContent = "x-dc{display:block}helmet{display:none}";
  document.head.appendChild(style);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
