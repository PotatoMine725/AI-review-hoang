/*
 * runtime.js — đổ dữ liệu cảnh (props) vào layout. Thuộc phần template (FE sửa được).
 *
 * Mỗi layout là một đoạn HTML; compose.py chèn nó vào index.html, bọc trong một host
 *   <div class="clip" data-scene="s01" data-start=… data-duration=… data-vars='{"props":…,"css":…}'>
 * Script cuối layout gọi TPL.mount("<layout>"); TPL đọc data-vars của host rồi điền vào:
 *   data-text="title"        → chữ của props.title (chuỗi hoặc {text, highlight})
 *   data-list="chips"        → lặp phần tử mẫu con [data-item] theo mảng props.chips
 *                              (không dùng <template>: HyperFrames coi <template> là vỏ composition)
 *   data-icon="icon"         → SVG Lucide theo tên trong props (hoặc data-icon-name="hash" cố định)
 *   data-src="image.src"     → src của <img>/<video>. compose.py đã ghi sẵn src tĩnh (HyperFrames
 *                              chỉ trích khung video có src + id ngay trong HTML), runtime ghi lại
 *                              cùng giá trị nên vẫn đúng khi FE xem thử layout bằng dữ liệu mẫu.
 *   data-if="callout"        → xoá phần tử nếu props.callout rỗng
 * Biến CSS (thời lượng, zoom, nhịp --b1…) lấy từ vars.css và gắn lên phần tử gốc của layout.
 * Nhịp theo câu (motion.css): mục danh sách có `at` (segment_id) nhận --beat = mốc câu đó; không có
 *   `at` thì lấy --b<n> với n = data-beat-from của danh sách + thứ tự mục. --beat-next = nhịp của
 *   mục sau (mục cuối: không có). Gốc layout nhận --first-<tên danh sách> = nhịp mục đầu.
 * Chữ động: phần tử có data-words được tách thành từng từ <span class="w" style="--w: i">.
 * Kiểu vào cảnh vars.transition → lớp tr-in-<kiểu> trên gốc layout.
 * Gốc layout được gắn lớp is-portrait (9:16) hoặc is-landscape (16:9): CSS của layout viết
 * ".layout-hook.is-portrait …". Mọi cảnh nằm chung một trang, nên selector của layout luôn bắt đầu
 * bằng .layout-<tên> để không ảnh hưởng layout khác.
 *
 * Không dùng requestAnimationFrame / setTimeout: mọi chuyển động là CSS animation, để HyperFrames
 * tua được theo từng khung (cùng đầu vào → cùng khung hình).
 */
(function () {
  "use strict";

  function get(obj, path) {
    return path.split(".").reduce(function (o, k) {
      return o == null ? undefined : o[k];
    }, obj);
  }

  function iconSvg(name) {
    var icons = window.TPL_ICONS || {};
    if (!icons[name]) throw new Error("Thiếu icon Lucide: " + name);
    return icons[name];
  }

  // Chữ có thể là chuỗi, hoặc {text, highlight}: phần highlight được bọc <mark> để tô màu nhấn.
  function setText(el, value) {
    if (value == null) return;
    var text = typeof value === "string" ? value : value.text;
    var hl = typeof value === "string" ? null : value.highlight;
    el.textContent = "";
    if (hl && text.indexOf(hl) >= 0) {
      var i = text.indexOf(hl);
      el.appendChild(document.createTextNode(text.slice(0, i)));
      var mark = document.createElement("mark");
      mark.textContent = hl;
      el.appendChild(mark);
      el.appendChild(document.createTextNode(text.slice(i + hl.length)));
    } else {
      el.textContent = text;
    }
  }

  // Phần tử thuộc về scope này (không nằm trong một data-list con, không nằm trong <template>).
  function own(scope, el) {
    if (el.closest("[data-item]")) return false;
    var list = el.parentElement && el.parentElement.closest("[data-list]");
    return !list || list === scope || !scope.contains(list);
  }

  // Tách chữ thành từng từ (giữ <mark> nguyên khối) để CSS cho hiện lần lượt.
  function splitWords(el) {
    var parts = [];
    Array.prototype.slice.call(el.childNodes).forEach(function (n) {
      if (n.nodeType === 3) {
        n.textContent.split(/(\s+)/).forEach(function (t) {
          if (t) parts.push(/^\s+$/.test(t) ? document.createTextNode(t) : t);
        });
      } else {
        parts.push(n);
      }
    });
    el.textContent = "";
    var w = 0;
    var last = null; // span trước đó, nếu không có khoảng trắng chen giữa
    parts.forEach(function (p) {
      if (typeof p !== "string" && p.nodeType === 3) {
        el.appendChild(p);
        last = null;
        return;
      }
      if (last) {
        // Dính liền từ trước (vd "<mark>miễn phí</mark>,"): gộp để không xuống dòng giữa chừng.
        if (typeof p === "string") last.appendChild(document.createTextNode(p));
        else last.appendChild(p);
        return;
      }
      var span = document.createElement("span");
      span.className = "w";
      span.style.setProperty("--w", String(w++));
      if (typeof p === "string") span.textContent = p;
      else span.appendChild(p);
      el.appendChild(span);
      last = span;
    });
  }

  function beatOf(item, i, list, ctx) {
    if (item && item.at && ctx.segAt[item.at] != null) return ctx.segAt[item.at];
    var from = list.getAttribute("data-beat-from");
    if (from == null) return null;
    var v = ctx.css["--b" + (parseInt(from, 10) + i)];
    return v == null ? null : parseFloat(v);
  }

  function fill(scope, data, ctx) {
    ctx = ctx || { segAt: {}, css: {}, root: scope };
    scope.querySelectorAll("[data-list]").forEach(function (list) {
      var items = get(data, list.getAttribute("data-list")) || [];
      var proto = list.querySelector("[data-item]");
      if (!proto) return;
      var beats = items.map(function (item, i) {
        return beatOf(item, i, list, ctx);
      });
      if (beats.length && beats[0] != null) {
        ctx.root.style.setProperty("--first-" + list.getAttribute("data-list"), beats[0] + "s");
      }
      items.forEach(function (item, i) {
        var node = proto.cloneNode(true);
        node.removeAttribute("data-item");
        node.style.setProperty("--i", String(i)); // thứ tự để CSS lệch thời điểm hiện
        if (beats[i] != null) node.style.setProperty("--beat", beats[i] + "s");
        if (beats[i + 1] != null) node.style.setProperty("--beat-next", beats[i + 1] + "s");
        if (item.accent) node.classList.add("is-accent");
        fill(node, item, ctx);
        // Phần tử gốc của item cũng có thể mang data-text / data-icon.
        if (node.hasAttribute("data-text")) setText(node, get(item, node.getAttribute("data-text")));
        list.appendChild(node);
      });
      proto.remove();
    });
    scope.querySelectorAll("[data-if]").forEach(function (el) {
      if (!own(scope, el)) return;
      var v = get(data, el.getAttribute("data-if"));
      if (!v || (Array.isArray(v) && v.length === 0)) el.remove();
    });
    scope.querySelectorAll("[data-text]").forEach(function (el) {
      if (!own(scope, el)) return;
      setText(el, get(data, el.getAttribute("data-text")));
    });
    scope.querySelectorAll("[data-words]").forEach(function (el) {
      if (!own(scope, el) || el.querySelector(".w")) return;
      splitWords(el);
    });
    scope.querySelectorAll("[data-icon], [data-icon-name]").forEach(function (el) {
      if (!own(scope, el)) return;
      var name = el.getAttribute("data-icon-name") || get(data, el.getAttribute("data-icon"));
      if (name) el.innerHTML = iconSvg(name);
    });
    scope.querySelectorAll("[data-src]").forEach(function (el) {
      if (!own(scope, el)) return;
      var src = get(data, el.getAttribute("data-src"));
      if (src) el.setAttribute("src", src);
    });
  }

  function mount(layout) {
    var roots = document.querySelectorAll('[data-layout="' + layout + '"]:not([data-mounted])');
    roots.forEach(function (root) {
      var host = root.closest("[data-scene]");
      var id = host ? host.getAttribute("data-scene") : "";
      var vars = host ? JSON.parse(host.getAttribute("data-vars") || "{}") : {};
      var props = vars.props || {};
      var css = vars.css || {};
      Object.keys(css).forEach(function (k) {
        root.style.setProperty(k, String(css[k]));
      });
      var portrait = document.querySelector("#root.r916") !== null;
      root.classList.add(portrait ? "is-portrait" : "is-landscape");
      if (vars.transition && vars.transition !== "none") {
        root.classList.add("tr-in-" + vars.transition);
      }
      fill(root, props, { segAt: vars.seg_at || {}, css: css, root: root });
      root.setAttribute("data-mounted", id || "");
    });
  }

  window.TPL = { mount: mount };
})();
