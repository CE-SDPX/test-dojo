/* DojoMart front-end. Vanilla JS, no build step. */
(function () {
  "use strict";

  var API_BASE = (window.DOJO_CONFIG && window.DOJO_CONFIG.apiBaseUrl) || "http://localhost:8001";
  var TOKEN_KEY = "dojo_token";
  var state = { user: null, menuOpen: false };

  // ---------- helpers ----------
  function imgUrl(path) { return API_BASE + path; }

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(s) {
    if (s === null || s === undefined) return "";
    var neg = s.toString().charAt(0) === "-";
    var v = neg ? s.toString().slice(1) : s.toString();
    var parts = v.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return (neg ? "-" : "") + "฿" + parts.join(".");
  }
  function fmtDateTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    function p(n) { return String(n).padStart(2, "0"); }
    return p(d.getDate()) + "/" + p(d.getMonth() + 1) + "/" + d.getFullYear() + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    function p(n) { return String(n).padStart(2, "0"); }
    return p(d.getMonth() + 1) + "/" + p(d.getDate()) + "/" + d.getFullYear();
  }
  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }

  function toast(msg, type) {
    var root = document.getElementById("toastRoot");
    var el = document.createElement("div");
    el.className = "toast" + (type === "error" ? " error" : "");
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(function () { el.remove(); }, 5000);
  }

  function confirmDialog(title, message, confirmLabel) {
    return new Promise(function (resolve) {
      var root = document.getElementById("dialogRoot");
      root.innerHTML =
        '<div class="dialog-overlay" role="dialog" aria-modal="true">' +
        '<div class="dialog-box">' +
        "<h2>" + esc(title) + "</h2>" +
        "<p>" + esc(message) + "</p>" +
        '<div class="dialog-actions">' +
        '<button class="secondary" id="dlgCancel">Cancel</button>' +
        '<button id="dlgConfirm">' + esc(confirmLabel) + "</button>" +
        "</div></div></div>";
      function close(result) {
        root.innerHTML = "";
        document.removeEventListener("keydown", onKey);
        resolve(result);
      }
      function onKey(e) { if (e.key === "Escape") close(false); }
      document.addEventListener("keydown", onKey);
      document.getElementById("dlgCancel").onclick = function () { close(false); };
      document.getElementById("dlgConfirm").onclick = function () { close(true); };
      document.getElementById("dlgCancel").focus();
    });
  }

  function api(method, path, opts) {
    opts = opts || {};
    var url = API_BASE + path;
    if (opts.qs) {
      var qs = Object.keys(opts.qs)
        .filter(function (k) { return opts.qs[k] !== undefined && opts.qs[k] !== null && opts.qs[k] !== ""; })
        .map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(opts.qs[k]); })
        .join("&");
      if (qs) url += "?" + qs;
    }
    var headers = {};
    var token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    var fetchOpts = { method: method, headers: headers };
    if (opts.formData) {
      // Content-Type (with multipart boundary) is set by the browser; do not set it ourselves.
      fetchOpts.body = opts.formData;
    } else if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      fetchOpts.body = JSON.stringify(opts.body);
    }
    return fetch(url, fetchOpts).then(function (resp) {
      if (resp.status === 204) return { status: resp.status, body: null };
      var ct = resp.headers.get("Content-Type") || "";
      if (ct.indexOf("text/csv") !== -1) {
        return resp.blob().then(function (blob) {
          return { status: resp.status, blob: blob, filename: parseFilename(resp.headers.get("Content-Disposition")) };
        });
      }
      return resp.json().catch(function () { return null; }).then(function (body) {
        if (resp.status === 401 && token) {
          clearToken();
          state.user = null;
          toast("Your session has expired. Please sign in again.", "error");
          navigate("/login");
        }
        if (!resp.ok) {
          var err = new Error((body && body.error && body.error.message) || "Request failed");
          err.status = resp.status;
          err.body = body;
          throw err;
        }
        return { status: resp.status, body: body };
      });
    });
  }
  function parseFilename(cd) {
    if (!cd) return "download.csv";
    var m = /filename="([^"]+)"/.exec(cd);
    return m ? m[1] : "download.csv";
  }
  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  function fieldErrors(err) {
    var out = {};
    if (err && err.body && err.body.error && err.body.error.details) {
      err.body.error.details.forEach(function (d) { out[d.field] = d.message; });
    }
    return out;
  }
  function errMessage(err) {
    return (err && err.body && err.body.error && err.body.error.message) || "Something went wrong. Please try again.";
  }

  // ---------- router ----------
  var routes = [];
  function route(pattern, handler, opts) {
    var keys = [];
    var re = new RegExp("^" + pattern.replace(/:[^/]+/g, function (m) { keys.push(m.slice(1)); return "([^/]+)"; }) + "$");
    routes.push({ re: re, keys: keys, handler: handler, opts: opts || {} });
  }
  function navigate(path) {
    if (location.pathname + location.search !== path) {
      history.pushState({}, "", path);
    }
    renderRoute();
  }
  window.addEventListener("popstate", renderRoute);
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a[data-link]");
    if (a) { e.preventDefault(); navigate(a.getAttribute("href")); }
  });

  function currentHome() {
    if (!state.user) return "/products";
    switch (state.user.role) {
      case "customer": return "/products";
      case "staff": return "/staff/orders";
      case "manager": return "/manager/reports";
      case "admin": return "/admin/users";
    }
    return "/products";
  }

  function requireSignIn(message) {
    toast(message || "Please sign in to continue.", "error");
    navigate("/login");
    return false;
  }

  function renderRoute() {
    var path = location.pathname;
    for (var i = 0; i < routes.length; i++) {
      var m = routes[i].re.exec(path);
      if (m) {
        var params = {};
        routes[i].keys.forEach(function (k, idx) { params[k] = decodeURIComponent(m[idx + 1]); });
        var opts = routes[i].opts;
        if (opts.public) {
          // login / register: signed-in users are sent to their own home
          if (state.user) { navigate(currentHome()); return; }
        } else if (opts.anon) {
          // open to everyone; roles (when given) only constrain signed-in users
          if (state.user && opts.roles && opts.roles.indexOf(state.user.role) === -1) {
            renderLayout(); mount(renderForbidden()); return;
          }
          if (state.user && state.user.must_change_password && path !== "/change-password") {
            navigate("/change-password"); return;
          }
        } else {
          if (!state.user) { navigate("/login"); return; }
          if (opts.roles && opts.roles.indexOf(state.user.role) === -1) {
            renderLayout(); mount(renderForbidden()); return;
          }
          if (state.user.must_change_password && path !== "/change-password") {
            navigate("/change-password"); return;
          }
        }
        renderLayout();
        routes[i].handler(params);
        return;
      }
    }
    renderLayout();
    mount(renderNotFound());
  }

  function mount(html) { document.getElementById("app").innerHTML = html; }

  // ---------- layout ----------
  var MENUS = {
    customer: [["/products", "Products"], ["/wishlist", "Wishlist"], ["/cart", "Cart"], ["/orders", "My orders"], ["/profile", "Profile"]],
    staff: [["/staff/orders", "Orders"], ["/staff/inventory", "Inventory"], ["/staff/low-stock", "Low stock"], ["/profile", "Profile"]],
    manager: [["/manager/reports", "Reports"], ["/manager/products", "Products"], ["/manager/coupons", "Coupons"], ["/profile", "Profile"]],
    admin: [["/admin/users", "Users"], ["/admin/jobs", "Jobs"], ["/staff/orders", "Orders"], ["/staff/inventory", "Inventory"],
      ["/staff/low-stock", "Low stock"], ["/manager/products", "Products"], ["/manager/coupons", "Coupons"],
      ["/manager/reports", "Reports"], ["/profile", "Profile"]],
  };

  function renderLayout() {
    var nav = document.getElementById("mainNav");
    var userBox = document.getElementById("headerUser");
    var searchBox = document.getElementById("headerSearch");
    var showSearch;
    if (!state.user) {
      nav.innerHTML = '<a data-link href="/products"' + (location.pathname === "/products" ? ' aria-current="page"' : "") + ">Products</a>";
      userBox.innerHTML = '<a data-link href="/login">Sign in</a> <a data-link href="/register">Create an account</a>';
      showSearch = true;
    } else {
      var items = MENUS[state.user.role] || [];
      nav.innerHTML = items.map(function (it) {
        var current = location.pathname === it[0];
        var label = it[0] === "/cart" ? '<span id="navCartLabel">' + esc(it[1]) + '</span>' : esc(it[1]);
        return '<a data-link href="' + it[0] + '"' + (current ? ' aria-current="page"' : "") + ">" + label + "</a>";
      }).join("");
      userBox.innerHTML = "Signed in as " + esc(state.user.display_name) + ' <a data-link href="#" id="signOutLink">Sign out</a>';
      document.getElementById("signOutLink").onclick = function (e) { e.preventDefault(); doLogout(); };
      showSearch = state.user.role === "customer";
      if (state.user.role === "customer") updateCartNavLabel();
    }
    if (showSearch) {
      searchBox.innerHTML = '<form id="headerSearchForm"><label class="visually-hidden" for="headerSearchInput">Search products</label>' +
        '<input id="headerSearchInput" type="search" placeholder="Search products" maxlength="100"></form>';
      document.getElementById("headerSearchForm").onsubmit = function (e) {
        e.preventDefault();
        var q = document.getElementById("headerSearchInput").value.trim();
        if (q.length > 100) { toast("Search text must be at most 100 characters.", "error"); return; }
        navigate("/products" + (q ? "?q=" + encodeURIComponent(q) : ""));
      };
    } else {
      searchBox.innerHTML = "";
    }
    document.getElementById("menuToggle").onclick = function () { nav.classList.toggle("open"); };
    api("GET", "/api/version").then(function (r) {
      document.getElementById("siteFooter").textContent = "DojoMart v" + r.body.version + " (" + r.body.source_hash.slice(0, 8) + ")";
    }).catch(function () {});
  }

  function updateCartNavLabel() {
    api("GET", "/api/cart").then(function (r) {
      var label = document.getElementById("navCartLabel");
      if (!label) return;
      var n = r.body.items.length;
      label.textContent = n > 0 ? "Cart (" + n + ")" : "Cart";
    }).catch(function () {});
  }

  function renderForbidden() {
    return '<h1>Access denied</h1><p>You do not have permission to view this page.</p>' +
      '<p><a data-link href="' + currentHome() + '">Go to my home page</a></p>';
  }
  function renderNotFound() {
    return '<h1>Page not found</h1><p>The page you are looking for does not exist.</p>' +
      '<p><a data-link href="' + currentHome() + '">Go to my home page</a></p>';
  }

  function doLogout() {
    api("POST", "/api/auth/logout").catch(function () {}).then(function () {
      clearToken(); state.user = null; navigate("/login");
    });
  }

  // ---------- Sign in / Register ----------
  function renderLogin() {
    mount(
      '<h1>Sign in</h1>' +
      '<form id="loginForm">' +
      '<div class="form-row"><label for="username">Username</label><input id="username" name="username" autocomplete="username" required></div>' +
      '<div class="form-row"><label for="password">Password</label><input id="password" type="password" name="password" autocomplete="current-password" required></div>' +
      '<div id="loginError" class="field-error"></div>' +
      '<button type="submit">Sign in</button>' +
      '</form>' +
      '<p><a data-link href="/register">Create an account</a></p>'
    );
    document.getElementById("loginForm").onsubmit = function (e) {
      e.preventDefault();
      var username = document.getElementById("username").value;
      var password = document.getElementById("password").value;
      document.getElementById("loginError").textContent = "";
      api("POST", "/api/auth/login", { body: { username: username, password: password } })
        .then(function (r) {
          setToken(r.body.token);
          state.user = r.body.user;
          state.user.must_change_password = r.body.must_change_password;
          navigate(r.body.must_change_password ? "/change-password" : currentHome());
        })
        .catch(function (err) { document.getElementById("loginError").textContent = errMessage(err); });
    };
  }

  function renderRegister() {
    mount(
      '<h1>Create an account</h1>' +
      '<form id="registerForm">' +
      '<div class="form-row"><label for="r_username">Username *</label><input id="r_username" required>' +
      '<div class="required-note" style="margin:4px 0">4 to 20 letters, digits or underscores.</div>' +
      '<div class="field-error" id="e_username"></div></div>' +
      '<div class="form-row"><label for="r_password">Password *</label><input id="r_password" type="password" required>' +
      '<div class="required-note" style="margin:4px 0">8 to 20 characters with at least one letter and one digit.</div>' +
      '<div class="field-error" id="e_password"></div></div>' +
      '<div class="form-row"><label for="r_confirm">Confirm password *</label><input id="r_confirm" type="password" required>' +
      '<div class="field-error" id="e_confirm"></div></div>' +
      '<div class="form-row"><label for="r_name">Display name *</label><input id="r_name" required>' +
      '<div class="field-error" id="e_display_name"></div></div>' +
      '<div class="form-row"><label for="r_birth">Date of birth *</label><input id="r_birth" type="date" required>' +
      '<div class="field-error" id="e_birthdate"></div></div>' +
      '<p class="required-note">* Required</p>' +
      '<button type="submit">Create account</button>' +
      '</form>' +
      '<p><a data-link href="/login">Already have an account? Sign in</a></p>'
    );
    document.getElementById("registerForm").onsubmit = function (e) {
      e.preventDefault();
      ["e_username", "e_password", "e_confirm", "e_display_name", "e_birthdate"].forEach(function (id) {
        document.getElementById(id).textContent = "";
      });
      var password = document.getElementById("r_password").value;
      var confirm = document.getElementById("r_confirm").value;
      if (password !== confirm) {
        document.getElementById("e_confirm").textContent = "Passwords do not match.";
        return;
      }
      var body = {
        username: document.getElementById("r_username").value,
        password: password,
        display_name: document.getElementById("r_name").value,
        birthdate: document.getElementById("r_birth").value,
      };
      api("POST", "/api/auth/register", { body: body })
        .then(function () { toast("Account created. Please sign in."); navigate("/login"); })
        .catch(function (err) {
          var fe = fieldErrors(err);
          Object.keys(fe).forEach(function (f) {
            var el = document.getElementById("e_" + f);
            if (el) el.textContent = fe[f];
          });
          if (err.status === 409) toast(errMessage(err), "error");
        });
    };
  }

  function renderChangePassword() {
    var forced = state.user.must_change_password;
    mount(
      (forced ? '<p class="field-error">You must change your password before continuing.</p>' : "") +
      '<h1>Change password</h1>' +
      '<form id="cpForm">' +
      '<div class="form-row"><label for="cp_current">Current password</label><input id="cp_current" type="password" required></div>' +
      '<div class="form-row"><label for="cp_new">New password</label><input id="cp_new" type="password" required></div>' +
      '<div class="form-row"><label for="cp_confirm">Confirm new password</label><input id="cp_confirm" type="password" required></div>' +
      '<div id="cpError" class="field-error"></div>' +
      '<button type="submit">Change password</button>' +
      '</form>'
    );
    document.getElementById("cpForm").onsubmit = function (e) {
      e.preventDefault();
      document.getElementById("cpError").textContent = "";
      var np = document.getElementById("cp_new").value;
      if (np !== document.getElementById("cp_confirm").value) {
        document.getElementById("cpError").textContent = "Passwords do not match.";
        return;
      }
      api("POST", "/api/auth/change-password", {
        body: { current_password: document.getElementById("cp_current").value, new_password: np },
      }).then(function () {
        toast("Password changed successfully.");
        state.user.must_change_password = false;
        navigate(currentHome());
      }).catch(function (err) { document.getElementById("cpError").textContent = errMessage(err); });
    };
  }

  // ---------- Products ----------
  function qsParams() {
    var out = {};
    new URLSearchParams(location.search).forEach(function (v, k) { out[k] = v; });
    return out;
  }
  function stockBadge(status) {
    if (status === "OUT_OF_STOCK") return '<span class="badge badge-danger">Out of stock</span>';
    if (status === "LOW_STOCK") return '<span class="badge badge-warn">Only a few left</span>';
    return '<span class="badge badge-ok">In stock</span>';
  }

  function renderProducts() {
    var p = qsParams();
    mount('<h1>Products</h1><div id="filters"></div><div id="productList">Loading&hellip;</div>');
    document.getElementById("filters").innerHTML =
      '<form id="filterForm" class="inline-form">' +
      '<div><label for="f_category">Category</label><select id="f_category">' +
      ["", "Drinkware", "Apparel", "Stationery", "Electronics", "Home"].map(function (c) {
        return '<option value="' + c + '"' + (p.category === c ? " selected" : "") + ">" + (c || "All categories") + "</option>";
      }).join("") + '</select></div>' +
      '<div><label for="f_min">Min price</label><input id="f_min" value="' + esc(p.min_price || "") + '"></div>' +
      '<div><label for="f_max">Max price</label><input id="f_max" value="' + esc(p.max_price || "") + '"></div>' +
      '<div><label for="f_sort">Sort by</label><select id="f_sort">' +
      [["name_asc", "Name (A–Z)"], ["name_desc", "Name (Z–A)"], ["price_asc", "Price (low to high)"], ["price_desc", "Price (high to low)"]].map(function (s) {
        return '<option value="' + s[0] + '"' + (p.sort === s[0] ? " selected" : "") + ">" + s[1] + "</option>";
      }).join("") + '</select></div>' +
      '<button type="submit">Apply filters</button>' +
      '<button type="button" class="secondary" id="clearFilters">Clear filters</button>' +
      '</form>';
    document.getElementById("filterForm").onsubmit = function (e) {
      e.preventDefault();
      var qp = { category: document.getElementById("f_category").value, min_price: document.getElementById("f_min").value,
        max_price: document.getElementById("f_max").value, sort: document.getElementById("f_sort").value, q: p.q };
      var qs = Object.keys(qp).filter(function (k) { return qp[k]; }).map(function (k) { return k + "=" + encodeURIComponent(qp[k]); }).join("&");
      navigate("/products" + (qs ? "?" + qs : ""));
    };
    document.getElementById("clearFilters").onclick = function () { navigate("/products" + (p.q ? "?q=" + encodeURIComponent(p.q) : "")); };

    api("GET", "/api/products", { qs: { q: p.q, category: p.category, min_price: p.min_price, max_price: p.max_price, sort: p.sort, page: p.page } })
      .then(function (r) {
        var body = r.body;
        var listEl = document.getElementById("productList");
        if (body.items.length === 0) {
          listEl.innerHTML = '<p class="empty-state">' + (p.q ? 'No products found for "' + esc(p.q) + '".' : "No products found.") + "</p>";
          return;
        }
        listEl.innerHTML = '<p>' + body.total_items + (body.total_items === 1 ? " product" : " products") + '</p>' +
          '<div class="product-grid">' + body.items.map(function (it) {
            return '<div class="product-card card">' +
              '<a data-link href="/products/' + it.id + '"><img src="' + imgUrl(it.image_url) + '" alt="Photo of ' + esc(it.name) + '" loading="lazy">' +
              "<h3>" + esc(it.name) + "</h3></a>" +
              '<p class="money">' + money(it.price) + "</p>" +
              "<p>" + (it.average_rating ? esc(it.average_rating) + " (" + it.review_count + (it.review_count === 1 ? " review" : " reviews") + ")" : "No reviews yet") + "</p>" +
              "<p>" + stockBadge(it.stock_status) + "</p>" +
              '<button data-add-cart="' + it.id + '"' + (it.stock_status === "OUT_OF_STOCK" ? " disabled" : "") + ">Add to cart</button>" +
              "</div>";
          }).join("") + "</div>" +
          '<div class="pagination">' +
          (body.page > 1 ? '<a data-link href="' + pageLink(p, body.page - 1) + '">Previous</a>' : "") +
          "<span>Page " + body.page + " of " + Math.max(1, body.total_pages) + "</span>" +
          (body.page < body.total_pages ? '<a data-link href="' + pageLink(p, body.page + 1) + '">Next</a>' : "") +
          "</div>";
        listEl.querySelectorAll("[data-add-cart]").forEach(function (btn) {
          btn.onclick = function () { addToCart(btn.getAttribute("data-add-cart"), 1); };
        });
      });
  }
  function pageLink(p, page) {
    var np = Object.assign({}, p, { page: page });
    var qs = Object.keys(np).filter(function (k) { return np[k]; }).map(function (k) { return k + "=" + encodeURIComponent(np[k]); }).join("&");
    return "/products" + (qs ? "?" + qs : "");
  }

  function addToCart(productId, quantity) {
    if (!state.user) { requireSignIn("Sign in to add items to your cart."); return; }
    api("POST", "/api/cart/items", { body: { product_id: Number(productId), quantity: quantity } })
      .then(function () { toast("Added to cart."); updateCartNavLabel(); })
      .catch(function (err) { toast(errMessage(err), "error"); });
  }

  function renderProductDetail(params) {
    mount('<p><a data-link href="/products">Back to products</a></p><div id="detail">Loading&hellip;</div>');
    var id = params.id;
    api("GET", "/api/products/" + id).then(function (r) {
      var it = r.body;
      document.getElementById("detail").innerHTML =
        '<div class="card">' +
        '<img src="' + imgUrl(it.image_url) + '" alt="Photo of ' + esc(it.name) + '" style="max-width:320px;width:100%;aspect-ratio:1/1;object-fit:cover">' +
        "<h1>" + esc(it.name) + "</h1>" +
        '<p class="money">' + money(it.price) + "</p>" +
        "<p>" + stockBadge(it.stock_status) + "</p>" +
        '<label for="qty">Quantity</label><select id="qty">' +
        Array.from({ length: 12 }, function (_, i) { return i + 1; }).map(function (n) { return '<option value="' + n + '">' + n + "</option>"; }).join("") +
        "</select>" +
        '<div style="margin-top:8px"><button id="addBtn"' + (it.stock_status === "OUT_OF_STOCK" ? " disabled" : "") + ">Add to cart</button> " +
        '<button class="secondary" id="wishBtn">' + (it.in_wishlist ? "Remove from wishlist" : "Add to wishlist") + "</button></div>" +
        "<h2>Description</h2><p>" + (it.description ? esc(it.description) : "—") + "</p>" +
        "<h2>Reviews</h2>" +
        "<p>" + (it.average_rating ? esc(it.average_rating) + " (" + it.review_count + (it.review_count === 1 ? " review" : " reviews") + ")" : "No reviews yet.") + "</p>" +
        '<div id="reviewForm"></div>' +
        '<div id="reviewList">Loading&hellip;</div>' +
        "</div>";
      document.getElementById("addBtn").onclick = function () {
        addToCart(id, Number(document.getElementById("qty").value));
      };
      document.getElementById("wishBtn").onclick = function () {
        if (!state.user) { requireSignIn("Sign in to save items to your wishlist."); return; }
        var method = it.in_wishlist ? "DELETE" : "PUT";
        api(method, "/api/wishlist/" + id).then(function () {
          toast(it.in_wishlist ? "Removed from wishlist." : "Added to wishlist.");
          renderProductDetail(params);
        }).catch(function (err) { toast(errMessage(err), "error"); });
      };
      if (state.user && state.user.role === "customer") {
        document.getElementById("reviewForm").innerHTML =
          '<form id="revForm"><h3>Write a review</h3>' +
          '<label for="rev_rating">Rating</label><select id="rev_rating">' +
          [1, 2, 3, 4, 5].map(function (n) { return '<option value="' + n + '">' + n + "</option>"; }).join("") + "</select>" +
          '<label for="rev_comment">Comment (optional)</label><textarea id="rev_comment" maxlength="500"></textarea>' +
          '<div id="revError" class="field-error"></div>' +
          '<button type="submit">Submit review</button></form>';
        document.getElementById("revForm").onsubmit = function (e) {
          e.preventDefault();
          api("POST", "/api/products/" + id + "/reviews", {
            body: { rating: Number(document.getElementById("rev_rating").value), comment: document.getElementById("rev_comment").value || null },
          }).then(function () {
            toast("Thank you for your review.");
            renderProductDetail(params);
          }).catch(function (err) { document.getElementById("revError").textContent = errMessage(err); });
        };
      } else if (!state.user) {
        document.getElementById("reviewForm").innerHTML = '<p><a data-link href="/login">Sign in</a> to write a review.</p>';
      }
      api("GET", "/api/products/" + id + "/reviews").then(function (rr) {
        var listEl = document.getElementById("reviewList");
        if (rr.body.items.length === 0) { listEl.innerHTML = "<p>No reviews yet.</p>"; return; }
        listEl.innerHTML = rr.body.items.map(function (rv) {
          return '<div class="card" style="margin-bottom:8px">' + "<strong>" + esc(rv.display_name) + "</strong> &mdash; Rating: " + rv.rating + "/5<br>" +
            '<span style="color:#595959">' + fmtDate(rv.created_at) + "</span>" + (rv.comment ? "<p>" + esc(rv.comment) + "</p>" : "") + "</div>";
        }).join("");
      });
    }).catch(function () { mount(renderNotFound()); });
  }

  // ---------- Wishlist ----------
  function renderWishlist() {
    mount('<h1>Wishlist</h1><div id="wishList">Loading&hellip;</div>');
    api("GET", "/api/wishlist").then(function (r) {
      var el = document.getElementById("wishList");
      if (r.body.items.length === 0) { el.innerHTML = '<p class="empty-state">Your wishlist is empty.</p>'; return; }
      el.innerHTML = r.body.items.map(function (it) {
        return '<div class="card" style="margin-bottom:8px;display:flex;gap:12px;align-items:center">' +
          '<a data-link href="/products/' + it.product_id + '"><img src="' + imgUrl(it.image_url) + '" alt="Photo of ' + esc(it.name) + '" style="width:64px;height:64px;object-fit:cover;border-radius:4px;flex-shrink:0"></a>' +
          '<div><a data-link href="/products/' + it.product_id + '">' + esc(it.name) + "</a> &mdash; " +
          '<span class="money">' + money(it.price) + "</span> " + stockBadge(it.stock_status) +
          ' <button data-add="' + it.product_id + '"' + (it.stock_status === "OUT_OF_STOCK" ? " disabled" : "") + ">Add to cart</button>" +
          ' <button class="secondary" data-remove="' + it.product_id + '">Remove</button></div></div>';
      }).join("");
      el.querySelectorAll("[data-add]").forEach(function (b) { b.onclick = function () { addToCart(b.getAttribute("data-add"), 1); }; });
      el.querySelectorAll("[data-remove]").forEach(function (b) {
        b.onclick = function () {
          api("DELETE", "/api/wishlist/" + b.getAttribute("data-remove")).then(function () { renderWishlist(); });
        };
      });
    });
  }

  // ---------- Cart ----------
  function renderCartBox(cart) {
    var pr = cart.pricing;
    return '<div class="pricing-box">' +
      row("Subtotal", pr.subtotal) + row("Volume discount", pr.volume_discount) + row("Coupon discount", pr.coupon_discount) +
      row("VAT (7%)", pr.vat) + row("Shipping", pr.shipping === "0.00" ? "Free" : money(pr.shipping), true) +
      '<div class="row total">' + "<span>Total</span><span class=\"money\">" + money(pr.grand_total) + "</span></div>" +
      "</div>";
    function row(label, value, raw) { return '<div class="row"><span>' + label + '</span><span class="money">' + (raw ? value : money(value)) + "</span></div>"; }
  }

  function renderCart() {
    mount('<h1>Cart</h1><div id="cartBody">Loading&hellip;</div>');
    loadCart();
  }
  function loadCart() {
    api("GET", "/api/cart").then(function (r) {
      var cart = r.body;
      var el = document.getElementById("cartBody");
      if (cart.items.length === 0) {
        el.innerHTML = '<p class="empty-state">Your cart is empty.</p><p><a data-link href="/products">Continue shopping</a></p>';
        return;
      }
      el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Product</th><th class="num">Unit price</th><th>Quantity</th><th class="num">Total</th><th></th></tr></thead><tbody>' +
        cart.items.map(function (it) {
          return "<tr><td>" + esc(it.name) + '</td><td class="num money">' + money(it.unit_price) + "</td><td>" +
            '<select data-qty="' + it.id + '">' + Array.from({ length: 10 }, function (_, i) { return i + 1; }).map(function (n) {
              return '<option value="' + n + '"' + (n === it.quantity ? " selected" : "") + ">" + n + "</option>";
            }).join("") + "</select></td>" +
            '<td class="num money">' + money(it.line_total) + '</td><td><button class="secondary" data-remove="' + it.id + '">Remove</button></td></tr>';
        }).join("") + "</tbody></table></div>" +
        '<form id="couponForm" class="inline-form"><div><label for="couponCode">Coupon code</label><input id="couponCode" value="' + esc(cart.coupon ? cart.coupon.code : "") + '"></div>' +
        '<button type="submit">Apply</button>' + (cart.coupon ? '<button type="button" class="secondary" id="removeCoupon">Remove coupon</button>' : "") + "</form>" +
        (cart.coupon ? "<p>" + (cart.coupon.valid ? "Coupon " + esc(cart.coupon.code) + " applied." : "Coupon " + esc(cart.coupon.code) + " is not applicable. " + esc(cart.coupon.message)) + "</p>" : "") +
        renderCartBox(cart) +
        '<p><a data-link href="/products">Continue shopping</a> <a class="btn" data-link href="/checkout">Checkout</a></p>';
      el.querySelectorAll("[data-qty]").forEach(function (sel) {
        sel.onchange = function () {
          api("PATCH", "/api/cart/items/" + sel.getAttribute("data-qty"), { body: { quantity: Number(sel.value) } })
            .then(loadCart).catch(function (err) { toast(errMessage(err), "error"); });
        };
      });
      el.querySelectorAll("[data-remove]").forEach(function (b) {
        b.onclick = function () { api("DELETE", "/api/cart/items/" + b.getAttribute("data-remove")).then(function () { updateCartNavLabel(); loadCart(); }); };
      });
      document.getElementById("couponForm").onsubmit = function (e) {
        e.preventDefault();
        api("PUT", "/api/cart/coupon", { body: { code: document.getElementById("couponCode").value } })
          .then(loadCart).catch(function (err) { toast(errMessage(err), "error"); });
      };
      var rc = document.getElementById("removeCoupon");
      if (rc) rc.onclick = function () { api("DELETE", "/api/cart/coupon").then(loadCart); };
    });
  }

  // ---------- Checkout ----------
  function renderCheckout() {
    mount('<h1>Checkout</h1><div id="checkoutBody">Loading&hellip;</div>');
    Promise.all([api("GET", "/api/cart"), api("GET", "/api/me/addresses")]).then(function (results) {
      var cart = results[0].body;
      var addresses = results[1].body.items;
      if (cart.items.length === 0) { navigate("/cart"); return; }
      var el = document.getElementById("checkoutBody");
      if (addresses.length === 0) {
        el.innerHTML = '<p class="field-error">Add a delivery address before placing an order. <a data-link href="/profile">Go to profile</a></p>';
        return;
      }
      el.innerHTML = "<h2>Delivery address</h2>" +
        addresses.map(function (a) {
          return '<label style="display:flex;gap:8px;align-items:flex-start;font-weight:normal"><input type="radio" name="addr" value="' + a.id + '"' + (a.is_default ? " checked" : "") + ">" +
            "<span>" + esc(a.label) + " — " + esc(a.recipient_name) + ", " + esc(a.phone) + "<br>" + esc(a.line1) + (a.line2 ? ", " + esc(a.line2) : "") + ", " + esc(a.province) + " " + esc(a.postal_code) + "</span></label>";
        }).join("") +
        "<h2>Order summary</h2>" +
        '<div class="table-wrap"><table><thead><tr><th>Product</th><th class="num">Quantity</th><th class="num">Total</th></tr></thead><tbody>' +
        cart.items.map(function (it) { return "<tr><td>" + esc(it.name) + '</td><td class="num">' + it.quantity + '</td><td class="num money">' + money(it.line_total) + "</td></tr>"; }).join("") +
        "</tbody></table></div>" + renderCartBox(cart) +
        '<button id="placeOrderBtn">Place order</button>';
      document.getElementById("placeOrderBtn").onclick = function () {
        var sel = el.querySelector('input[name="addr"]:checked');
        if (!sel) { toast("Select a delivery address.", "error"); return; }
        var btn = document.getElementById("placeOrderBtn");
        btn.disabled = true; btn.textContent = "Placing order…";
        api("POST", "/api/orders", { body: { address_id: Number(sel.value) } })
          .then(function (r) { navigate("/orders/" + r.body.id + "/confirmation"); })
          .catch(function (err) { toast(errMessage(err), "error"); btn.disabled = false; btn.textContent = "Place order"; });
      };
    });
  }

  // ---------- Orders ----------
  var STATUS_LABELS = {
    PENDING_PAYMENT: "Pending payment", PAID: "Paid", PACKED: "Packed", SHIPPED: "Shipped",
    DELIVERED: "Delivered", CANCELLED: "Canceled", RETURNED: "Returned",
  };
  function statusBadge(s) {
    var cls = s === "CANCELLED" ? "badge-danger" : (s === "DELIVERED" || s === "PAID" ? "badge-ok" : "badge-warn");
    return '<span class="badge ' + cls + '">' + STATUS_LABELS[s] + "</span>";
  }

  function renderOrderConfirmation(params) {
    mount('<div id="confBody">Loading&hellip;</div>');
    api("GET", "/api/orders/" + params.id).then(function (r) {
      var o = r.body;
      var el = document.getElementById("confBody");
      el.innerHTML = "<h1>Thank you for your order</h1><p>Your order #" + o.id + " has been placed.</p>" +
        '<p>Total to pay: <span class="money">' + money(o.pricing.grand_total) + "</span></p>";
      if (o.status === "PENDING_PAYMENT") {
        el.innerHTML += '<p>Your order will be cancelled automatically if it is not paid within 60 minutes.</p>' +
          '<form id="payForm"><label for="payMethod">Payment method</label><select id="payMethod">' +
          '<option value="CARD">Credit/debit card</option><option value="PROMPTPAY">PromptPay</option></select>' +
          '<button type="submit">Pay now</button></form>';
        document.getElementById("payForm").onsubmit = function (e) {
          e.preventDefault();
          api("POST", "/api/orders/" + o.id + "/pay", { body: { method: document.getElementById("payMethod").value } })
            .then(function () { toast("Payment received."); navigate("/orders/" + o.id); })
            .catch(function (err) { toast(errMessage(err), "error"); });
        };
      }
      el.innerHTML += '<p><a data-link href="/orders">Go to my orders</a></p>';
    });
  }

  function renderMyOrders() {
    var p = qsParams();
    mount('<h1>My orders</h1><div id="ordersFilter"></div><div id="ordersBody">Loading&hellip;</div>');
    document.getElementById("ordersFilter").innerHTML =
      '<label for="statusFilter">Status</label><select id="statusFilter"><option value="">All statuses</option>' +
      Object.keys(STATUS_LABELS).map(function (s) { return '<option value="' + s + '"' + (p.status === s ? " selected" : "") + ">" + STATUS_LABELS[s] + "</option>"; }).join("") +
      "</select>";
    document.getElementById("statusFilter").onchange = function (e) {
      navigate("/orders" + (e.target.value ? "?status=" + e.target.value : ""));
    };
    api("GET", "/api/orders", { qs: { status: p.status, page: p.page } }).then(function (r) {
      var el = document.getElementById("ordersBody");
      if (r.body.items.length === 0) { el.innerHTML = '<p class="empty-state">You have not placed any orders yet.</p>'; return; }
      el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Order</th><th>Date</th><th>Status</th><th>Items</th><th class="num">Total</th><th></th></tr></thead><tbody>' +
        r.body.items.map(function (o) {
          return "<tr><td>#" + o.id + "</td><td>" + fmtDateTime(o.created_at) + "</td><td>" + statusBadge(o.status) + "</td><td>" + o.item_count +
            '</td><td class="num money">' + money(o.grand_total) + '</td><td><a data-link href="/orders/' + o.id + '">View</a></td></tr>';
        }).join("") + "</tbody></table></div>";
    });
  }

  function renderOrderDetail(params) {
    mount('<div id="orderBody">Loading&hellip;</div>');
    load();
    function load() {
      api("GET", "/api/orders/" + params.id).then(function (r) {
        var o = r.body;
        var el = document.getElementById("orderBody");
        el.innerHTML = "<h1>Order #" + o.id + "</h1>" + statusBadge(o.status) +
          "<h2>Items</h2><div class=\"table-wrap\"><table><thead><tr><th>Product</th><th class=\"num\">Unit price</th><th class=\"num\">Qty</th><th class=\"num\">Total</th></tr></thead><tbody>" +
          o.items.map(function (it) { return "<tr><td>" + esc(it.name) + '</td><td class="num money">' + money(it.unit_price) + '</td><td class="num">' + it.quantity + '</td><td class="num money">' + money(it.line_total) + "</td></tr>"; }).join("") +
          "</tbody></table></div>" +
          "<h2>Delivery address</h2><p>" + esc(o.address.label) + " — " + esc(o.address.recipient_name) + ", " + esc(o.address.phone) + "<br>" +
          esc(o.address.line1) + (o.address.line2 ? ", " + esc(o.address.line2) : "") + ", " + esc(o.address.province) + " " + esc(o.address.postal_code) + "</p>" +
          "<h2>Payment summary</h2>" + renderCartBox(o) +
          (o.refund_amount !== "0.00" ? '<p>Refunded amount: <span class="money">' + money(o.refund_amount) + "</span></p>" : "") +
          (o.return_deadline ? "<p>Return by " + fmtDateTime(o.return_deadline) + "</p>" : "") +
          "<h2>Timeline</h2><ul>" +
          ["created_at|Placed", "paid_at|Paid", "packed_at|Packed", "shipped_at|Shipped", "delivered_at|Delivered", "cancelled_at|Cancelled", "returned_at|Returned"]
            .map(function (pair) { var kv = pair.split("|"); return o[kv[0]] ? "<li>" + kv[1] + ": " + fmtDateTime(o[kv[0]]) + "</li>" : ""; }).join("") +
          "</ul><div id=\"orderActions\"></div>";
        var actions = document.getElementById("orderActions");
        var html = "";
        if (o.status === "PENDING_PAYMENT") html += '<button id="payBtn">Pay now</button> ';
        if (o.status === "PENDING_PAYMENT" || o.status === "PAID") html += '<button class="danger" id="cancelBtn">Cancel order</button> ';
        if (o.status === "DELIVERED" && o.return_deadline && new Date(o.return_deadline) > new Date()) html += '<button id="returnBtn">Return order</button>';
        actions.innerHTML = html;
        if (document.getElementById("payBtn")) document.getElementById("payBtn").onclick = function () { navigate("/orders/" + o.id + "/confirmation"); };
        if (document.getElementById("cancelBtn")) document.getElementById("cancelBtn").onclick = function () {
          confirmDialog("Cancel order", "Cancel this order?", "Yes, cancel").then(function (ok) {
            if (!ok) return;
            api("POST", "/api/orders/" + o.id + "/cancel").then(function () { toast("Order cancelled."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
          });
        };
        if (document.getElementById("returnBtn")) document.getElementById("returnBtn").onclick = function () {
          confirmDialog("Return order", "Return this order? The full amount will be refunded.", "Yes, return").then(function (ok) {
            if (!ok) return;
            api("POST", "/api/orders/" + o.id + "/return").then(function () { toast("Order returned."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
          });
        };
      }).catch(function () { mount(renderNotFound()); });
    }
  }

  // ---------- Profile ----------
  function renderProfile() {
    mount('<h1>Profile</h1><div id="profileBody">Loading&hellip;</div>');
    api("GET", "/api/me").then(function (r) {
      var me = r.body;
      var isCustomer = me.role === "customer";
      var el = document.getElementById("profileBody");
      el.innerHTML = '<form id="profileForm">' +
        '<div class="form-row"><label>Username</label><input value="' + esc(me.username) + '" disabled></div>' +
        '<div class="form-row"><label for="p_name">Display name</label><input id="p_name" value="' + esc(me.display_name) + '"></div>' +
        (isCustomer ? '<div class="form-row"><label for="p_phone">Phone</label><input id="p_phone" value="' + esc(me.phone || "") + '"></div>' +
          '<div class="form-row"><label>Date of birth</label><input value="' + esc(me.birthdate || "") + '" disabled></div>' : "") +
        '<div id="profileError" class="field-error"></div>' +
        '<button type="submit">Save changes</button></form>' +
        '<p><a data-link href="/change-password">Change password</a></p>';
      document.getElementById("profileForm").onsubmit = function (e) {
        e.preventDefault();
        var body = { display_name: document.getElementById("p_name").value };
        if (isCustomer) body.phone = document.getElementById("p_phone").value;
        api("PUT", "/api/me", { body: body }).then(function (rr) {
          toast("Profile updated.");
          state.user.display_name = rr.body.display_name;
          renderLayout();
        }).catch(function (err) { document.getElementById("profileError").textContent = errMessage(err); });
      };
      if (isCustomer) renderAddresses();
    });
  }
  function renderAddresses() {
    var container = document.createElement("div");
    container.id = "addressesSection";
    document.getElementById("profileBody").appendChild(container);
    load();
    function load() {
      api("GET", "/api/me/addresses").then(function (r) {
        var items = r.body.items;
        container.innerHTML = "<h2>Addresses</h2>" +
          (items.length === 0 ? '<p class="empty-state">You have no saved addresses.</p>' :
            items.map(function (a) {
              return '<div class="card" style="margin-bottom:8px">' + (a.is_default ? '<span class="badge badge-ok">Default</span> ' : "") +
                "<strong>" + esc(a.label) + "</strong><br>" + esc(a.recipient_name) + ", " + esc(a.phone) + "<br>" +
                esc(a.line1) + (a.line2 ? ", " + esc(a.line2) : "") + ", " + esc(a.province) + " " + esc(a.postal_code) +
                '<div style="margin-top:8px"><button class="secondary" data-edit="' + a.id + '">Edit</button> ' +
                (a.is_default ? "" : '<button class="secondary" data-default="' + a.id + '">Set as default</button> ') +
                '<button class="danger" data-delete="' + a.id + '">Delete</button></div></div>';
            }).join("")) +
          (items.length < 5 ? '<p>You can save up to 5 addresses.</p><button id="addAddrBtn">Add address</button>' : "") +
          '<div id="addrFormBox"></div>';
        container.querySelectorAll("[data-delete]").forEach(function (b) {
          b.onclick = function () {
            confirmDialog("Delete address", "Delete this address?", "Delete").then(function (ok) {
              if (!ok) return;
              api("DELETE", "/api/me/addresses/" + b.getAttribute("data-delete")).then(function () { toast("Address deleted."); load(); });
            });
          };
        });
        container.querySelectorAll("[data-default]").forEach(function (b) {
          b.onclick = function () { api("POST", "/api/me/addresses/" + b.getAttribute("data-default") + "/default").then(function () { toast("Default address updated."); load(); }); };
        });
        container.querySelectorAll("[data-edit]").forEach(function (b) {
          b.onclick = function () { showAddressForm(items.find(function (x) { return x.id == b.getAttribute("data-edit"); })); };
        });
        var addBtn = document.getElementById("addAddrBtn");
        if (addBtn) addBtn.onclick = function () { showAddressForm(null); };
      });
    }
    function showAddressForm(addr) {
      var box = document.getElementById("addrFormBox");
      box.innerHTML = '<form id="addrForm" class="card">' +
        field("label", "Label", addr) + field("recipient_name", "Recipient name", addr) + field("phone", "Phone", addr) +
        field("line1", "Address line 1", addr) + field("line2", "Address line 2 (optional)", addr) +
        field("province", "Province", addr) + field("postal_code", "Postal code", addr) +
        '<div id="addrError" class="field-error"></div>' +
        '<button type="submit">Save address</button> <button type="button" class="secondary" id="addrCancel">Cancel</button></form>';
      function field(id, label, a) {
        return '<div class="form-row"><label for="a_' + id + '">' + label + '</label><input id="a_' + id + '" value="' + esc(a ? a[id] || "" : "") + '"></div>';
      }
      document.getElementById("addrCancel").onclick = function () { box.innerHTML = ""; };
      document.getElementById("addrForm").onsubmit = function (e) {
        e.preventDefault();
        var body = {};
        ["label", "recipient_name", "phone", "line1", "line2", "province", "postal_code"].forEach(function (f) {
          body[f] = document.getElementById("a_" + f).value;
        });
        var req = addr ? api("PUT", "/api/me/addresses/" + addr.id, { body: body }) : api("POST", "/api/me/addresses", { body: body });
        req.then(function () { toast("Address saved."); box.innerHTML = ""; load(); })
          .catch(function (err) { document.getElementById("addrError").textContent = errMessage(err); });
      };
    }
  }

  // ---------- Staff: Orders ----------
  function renderStaffOrders() {
    var p = qsParams();
    mount('<h1>Orders</h1><div id="staffOrdersFilter"></div><div id="staffOrdersBody">Loading&hellip;</div>');
    document.getElementById("staffOrdersFilter").innerHTML =
      '<form id="soFilter" class="inline-form"><div><label for="so_q">Search</label><input id="so_q" placeholder="Search by order number or username" value="' + esc(p.q || "") + '"></div>' +
      '<div><label for="so_status">Status</label><select id="so_status"><option value="">All statuses</option>' +
      Object.keys(STATUS_LABELS).map(function (s) { return '<option value="' + s + '"' + (p.status === s ? " selected" : "") + ">" + STATUS_LABELS[s] + "</option>"; }).join("") +
      '</select></div><button type="submit">Apply filters</button></form>';
    document.getElementById("soFilter").onsubmit = function (e) {
      e.preventDefault();
      var qp = { q: document.getElementById("so_q").value, status: document.getElementById("so_status").value };
      navigate("/staff/orders" + buildQs(qp));
    };
    load();
    function load() {
      api("GET", "/api/manage/orders", { qs: { q: p.q, status: p.status, page: p.page } }).then(function (r) {
        var el = document.getElementById("staffOrdersBody");
        if (r.body.items.length === 0) { el.innerHTML = '<p class="empty-state">No orders found.</p>'; return; }
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>Status</th><th class="num">Total</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (o) {
            var actions = "";
            if (o.status === "PAID") actions = '<button data-next="' + o.id + '" data-to="PACKED">Mark as packed</button> <button class="danger" data-cancel="' + o.id + '">Cancel order</button>';
            else if (o.status === "PACKED") actions = '<button data-next="' + o.id + '" data-to="SHIPPED">Mark as shipped</button> <button class="danger" data-cancel="' + o.id + '">Cancel order</button>';
            else if (o.status === "SHIPPED") actions = '<button data-next="' + o.id + '" data-to="DELIVERED">Mark as delivered</button>';
            else if (o.status === "PENDING_PAYMENT") actions = '<button class="danger" data-cancel="' + o.id + '">Cancel order</button>';
            return "<tr><td>#" + o.id + "</td><td>" + esc(o.customer.display_name) + "</td><td>" + fmtDateTime(o.created_at) + "</td><td>" + statusBadge(o.status) +
              '</td><td class="num money">' + money(o.grand_total) + "</td><td>" + actions + "</td></tr>";
          }).join("") + "</tbody></table></div>";
        el.querySelectorAll("[data-next]").forEach(function (b) {
          b.onclick = function () {
            api("PATCH", "/api/manage/orders/" + b.getAttribute("data-next") + "/status", { body: { status: b.getAttribute("data-to") } })
              .then(function () { toast("Order updated."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
          };
        });
        el.querySelectorAll("[data-cancel]").forEach(function (b) {
          b.onclick = function () {
            confirmDialog("Cancel order", "Cancel this order?", "Yes, cancel").then(function (ok) {
              if (!ok) return;
              api("POST", "/api/orders/" + b.getAttribute("data-cancel") + "/cancel").then(function () { toast("Order updated."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
            });
          };
        });
      });
    }
  }
  function buildQs(obj) {
    var qs = Object.keys(obj).filter(function (k) { return obj[k]; }).map(function (k) { return k + "=" + encodeURIComponent(obj[k]); }).join("&");
    return qs ? "?" + qs : "";
  }

  // ---------- Staff: Inventory ----------
  function renderStaffInventory() {
    var p = qsParams();
    mount('<h1>Inventory</h1><div id="invFilter"></div><div id="invBody">Loading&hellip;</div>');
    document.getElementById("invFilter").innerHTML = '<form id="invFilterForm"><label for="inv_q">Search</label>' +
      '<input id="inv_q" placeholder="Search by product name" value="' + esc(p.q || "") + '"><button type="submit">Apply filters</button></form>';
    document.getElementById("invFilterForm").onsubmit = function (e) { e.preventDefault(); navigate("/staff/inventory" + buildQs({ q: document.getElementById("inv_q").value })); };
    load();
    function load() {
      api("GET", "/api/manage/inventory", { qs: { q: p.q, page: p.page } }).then(function (r) {
        var el = document.getElementById("invBody");
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>SKU</th><th>Product</th><th class="num">Stock</th><th>Status</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (it) {
            return "<tr><td>" + esc(it.sku) + "</td><td>" + esc(it.name) + '</td><td class="num">' + it.stock + "</td><td>" +
              (it.active ? '<span class="badge badge-ok">Active</span>' : '<span class="badge">Inactive</span>') + "</td><td>" +
              '<button data-adjust="' + it.product_id + '">Adjust stock</button> <a data-link href="/staff/inventory/' + it.product_id + '/history">History</a></td></tr>';
          }).join("") + "</tbody></table></div><div id=\"adjustBox\"></div>";
        el.querySelectorAll("[data-adjust]").forEach(function (b) {
          b.onclick = function () { showAdjustForm(b.getAttribute("data-adjust")); };
        });
      });
    }
    function showAdjustForm(productId) {
      var box = document.getElementById("adjustBox");
      box.innerHTML = '<form id="adjustForm" class="card"><h3>Adjust stock</h3>' +
        '<label for="adj_delta">Quantity change</label><input id="adj_delta" type="number" required>' +
        '<label for="adj_reason">Reason</label><select id="adj_reason">' +
        '<option value="RECEIVE">Received</option><option value="DAMAGE">Damaged</option><option value="CORRECTION">Correction</option></select>' +
        '<p class="required-note">Use a positive number to add stock and a negative number to remove it.</p>' +
        '<div id="adjError" class="field-error"></div>' +
        '<button type="submit">Save</button> <button type="button" class="secondary" id="adjCancel">Cancel</button></form>';
      document.getElementById("adjCancel").onclick = function () { box.innerHTML = ""; };
      document.getElementById("adjustForm").onsubmit = function (e) {
        e.preventDefault();
        api("POST", "/api/manage/inventory/adjustments", {
          body: { product_id: Number(productId), delta: Number(document.getElementById("adj_delta").value), reason: document.getElementById("adj_reason").value },
        }).then(function () { toast("Stock updated."); box.innerHTML = ""; load(); })
          .catch(function (err) { document.getElementById("adjError").textContent = errMessage(err); });
      };
    }
  }
  function renderStaffInventoryHistory(params) {
    mount('<h1>Stock history</h1><div id="histBody">Loading&hellip;</div>');
    api("GET", "/api/manage/inventory/movements", { qs: { product_id: params.id } }).then(function (r) {
      var el = document.getElementById("histBody");
      var labels = { RECEIVE: "Received", DAMAGE: "Damaged", CORRECTION: "Correction", ORDER: "Order", CANCEL: "Order cancelled", RETURN: "Returned order" };
      if (r.body.items.length === 0) { el.innerHTML = '<p class="empty-state">No history found.</p>'; return; }
      el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Date</th><th class="num">Change</th><th class="num">Stock after</th><th>Reason</th><th>By</th></tr></thead><tbody>' +
        r.body.items.map(function (m) {
          return "<tr><td>" + fmtDateTime(m.created_at) + '</td><td class="num">' + (m.delta > 0 ? "+" : "") + m.delta + '</td><td class="num">' + m.stock_after +
            "</td><td>" + (labels[m.reason] || m.reason) + "</td><td>" + esc(m.actor) + "</td></tr>";
        }).join("") + "</tbody></table></div>";
    });
  }

  function renderStaffLowStock() {
    mount('<h1>Low stock</h1><div id="lowStockBody">Loading&hellip;</div>');
    api("GET", "/api/manage/inventory/low-stock").then(function (r) {
      var el = document.getElementById("lowStockBody");
      var header = r.body.taken_at ? "<p>Snapshot taken at " + fmtDateTime(r.body.taken_at) + "</p>" : "<p>No snapshot has been taken yet.</p>";
      if (r.body.items.length === 0) { el.innerHTML = header + '<p class="empty-state">No products are low on stock.</p>'; return; }
      el.innerHTML = header + '<div class="table-wrap"><table><thead><tr><th>SKU</th><th>Product</th><th class="num">Stock</th></tr></thead><tbody>' +
        r.body.items.map(function (it) { return "<tr><td>" + esc(it.sku) + "</td><td>" + esc(it.name) + '</td><td class="num">' + it.stock + "</td></tr>"; }).join("") +
        "</tbody></table></div>";
    });
  }

  // ---------- Manager: Products ----------
  function renderManagerProducts() {
    var p = qsParams();
    mount('<h1>Manage products</h1><div id="mpFilter"></div><div id="mpBody">Loading&hellip;</div><div id="mpFormBox"></div>');
    document.getElementById("mpFilter").innerHTML = '<form id="mpFilterForm" class="inline-form"><div><label for="mp_q">Search</label>' +
      '<input id="mp_q" placeholder="Search by name or SKU" value="' + esc(p.q || "") + '"></div><button type="submit">Apply filters</button>' +
      '<button type="button" id="mpAdd">Add product</button></form>';
    document.getElementById("mpFilterForm").onsubmit = function (e) { e.preventDefault(); navigate("/manager/products" + buildQs({ q: document.getElementById("mp_q").value })); };
    document.getElementById("mpAdd").onclick = function () { showForm(null); };
    load();
    function load() {
      api("GET", "/api/manage/products", { qs: { q: p.q, page: p.page } }).then(function (r) {
        var el = document.getElementById("mpBody");
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Image</th><th>SKU</th><th>Name</th><th>Category</th><th class="num">Price</th><th class="num">Stock</th><th>Status</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (it) {
            return "<tr><td><img src=\"" + imgUrl(it.image_url) + "\" alt=\"Photo of " + esc(it.name) + "\" style=\"width:48px;height:48px;object-fit:cover;border-radius:4px\"></td><td>" + esc(it.sku) + "</td><td>" + esc(it.name) + "</td><td>" + esc(it.category) + '</td><td class="num money">' + money(it.price) +
              '</td><td class="num">' + it.stock + "</td><td>" + (it.active ? '<span class="badge badge-ok">Active</span>' : '<span class="badge">Inactive</span>') + "</td><td>" +
              '<button class="secondary" data-edit="' + it.id + '">Edit</button> ' +
              '<button class="secondary" data-image="' + it.id + '">' + (it.has_image ? "Replace image" : "Upload image") + '</button> ' +
              '<button class="secondary" data-toggle="' + it.id + '" data-active="' + (it.active ? 0 : 1) + '">' + (it.active ? "Deactivate" : "Activate") + "</button></td></tr>";
          }).join("") + "</tbody></table></div>";
        el.querySelectorAll("[data-edit]").forEach(function (b) {
          var item = r.body.items.find(function (x) { return x.id == b.getAttribute("data-edit"); });
          b.onclick = function () { showForm(item); };
        });
        el.querySelectorAll("[data-image]").forEach(function (b) {
          var item = r.body.items.find(function (x) { return x.id == b.getAttribute("data-image"); });
          b.onclick = function () { showImageForm(item); };
        });
        el.querySelectorAll("[data-toggle]").forEach(function (b) {
          b.onclick = function () {
            var activate = b.getAttribute("data-active") === "1";
            var go = function () {
              api("PATCH", "/api/manage/products/" + b.getAttribute("data-toggle") + "/active", { body: { active: activate } })
                .then(function () { toast("Product saved."); load(); });
            };
            if (activate) go();
            else confirmDialog("Deactivate product", "Deactivate this product? It will be removed from all carts and wishlists.", "Deactivate").then(function (ok) { if (ok) go(); });
          };
        });
      });
    }
    function showImageForm(item) {
      var box = document.getElementById("mpFormBox");
      box.innerHTML = '<form id="mpImageForm" class="card"><h3>' + (item.has_image ? "Replace image" : "Upload image") + " — " + esc(item.name) + "</h3>" +
        '<label for="mp_image">Image file</label><input id="mp_image" type="file" accept="image/jpeg,.jpg">' +
        '<p class="required-note">JPEG (.jpg) only, up to 2 MB.</p>' +
        '<div id="mpImageError" class="field-error"></div>' +
        '<button type="submit">Upload</button> <button type="button" class="secondary" id="mpImageCancel">Cancel</button></form>';
      document.getElementById("mpImageCancel").onclick = function () { box.innerHTML = ""; };
      document.getElementById("mpImageForm").onsubmit = function (e) {
        e.preventDefault();
        var errEl = document.getElementById("mpImageError");
        errEl.textContent = "";
        var input = document.getElementById("mp_image");
        var file = input.files[0];
        if (!file) { errEl.textContent = "This field is required."; return; }
        if (!/\.jpe?g$/i.test(file.name) || (file.type && file.type !== "image/jpeg")) {
          errEl.textContent = "Image must be a JPEG file (.jpg)."; return;
        }
        if (file.size > 2 * 1024 * 1024) { errEl.textContent = "Image must be at most 2 MB."; return; }
        var fd = new FormData();
        fd.append("image", file, "image.jpg");
        api("POST", "/api/manage/products/" + item.id + "/image", { formData: fd })
          .then(function () { toast("Product saved."); box.innerHTML = ""; load(); })
          .catch(function (err) { var fe = fieldErrors(err); errEl.textContent = fe.image || errMessage(err); });
      };
    }
    function showForm(item) {
      var box = document.getElementById("mpFormBox");
      box.innerHTML = '<form id="mpForm" class="card"><h3>' + (item ? "Edit product" : "Add product") + "</h3>" +
        (item ? "" : '<div class="form-row"><label for="mp_sku">SKU</label><input id="mp_sku"></div>') +
        '<div class="form-row"><label for="mp_name">Name</label><input id="mp_name" value="' + esc(item ? item.name : "") + '"></div>' +
        '<div class="form-row"><label for="mp_desc">Description</label><textarea id="mp_desc">' + esc(item ? item.description || "" : "") + '</textarea></div>' +
        '<div class="form-row"><label for="mp_cat">Category</label><select id="mp_cat">' +
        ["Drinkware", "Apparel", "Stationery", "Electronics", "Home"].map(function (c) { return '<option value="' + c + '"' + (item && item.category === c ? " selected" : "") + ">" + c + "</option>"; }).join("") +
        '</select></div><div class="form-row"><label for="mp_price">Price</label><input id="mp_price" value="' + esc(item ? item.price : "") + '"></div>' +
        (item ? "" : '<div class="form-row"><label for="mp_stock">Initial stock</label><input id="mp_stock" value="0"></div>') +
        '<div id="mpError" class="field-error"></div>' +
        '<button type="submit">Save product</button> <button type="button" class="secondary" id="mpCancel">Cancel</button></form>';
      document.getElementById("mpCancel").onclick = function () { box.innerHTML = ""; };
      document.getElementById("mpForm").onsubmit = function (e) {
        e.preventDefault();
        var body = { name: document.getElementById("mp_name").value, description: document.getElementById("mp_desc").value || null,
          category: document.getElementById("mp_cat").value, price: document.getElementById("mp_price").value };
        var req;
        if (item) req = api("PUT", "/api/manage/products/" + item.id, { body: body });
        else { body.sku = document.getElementById("mp_sku").value; body.stock = Number(document.getElementById("mp_stock").value || 0); req = api("POST", "/api/manage/products", { body: body }); }
        req.then(function () { toast("Product saved."); box.innerHTML = ""; load(); })
          .catch(function (err) { document.getElementById("mpError").textContent = errMessage(err); });
      };
    }
  }

  // ---------- Manager: Coupons ----------
  function renderManagerCoupons() {
    var p = qsParams();
    mount('<h1>Coupons</h1><div id="mcFilter"></div><div id="mcBody">Loading&hellip;</div><div id="mcFormBox"></div>');
    document.getElementById("mcFilter").innerHTML = '<form id="mcFilterForm" class="inline-form"><div><label for="mc_q">Search</label>' +
      '<input id="mc_q" placeholder="Search by code" value="' + esc(p.q || "") + '"></div><button type="submit">Apply filters</button>' +
      '<button type="button" id="mcAdd">Add coupon</button></form>';
    document.getElementById("mcFilterForm").onsubmit = function (e) { e.preventDefault(); navigate("/manager/coupons" + buildQs({ q: document.getElementById("mc_q").value })); };
    document.getElementById("mcAdd").onclick = function () { showForm(null); };
    var STATUS_BADGE = { ACTIVE: "badge-ok", SCHEDULED: "badge-warn", EXPIRED: "badge-danger", DISABLED: "badge" };
    load();
    function load() {
      api("GET", "/api/manage/coupons", { qs: { q: p.q, page: p.page } }).then(function (r) {
        var el = document.getElementById("mcBody");
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Code</th><th>Type</th><th>Discount</th><th>Min. spend</th><th>Starts</th><th>Expires</th><th class="num">Used</th><th>Status</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (c) {
            var disc = c.type === "PERCENT" ? c.percent_off + "%" + (c.max_discount ? " (max " + money(c.max_discount) + ")" : "") : money(c.amount_off);
            return "<tr><td>" + esc(c.code) + "</td><td>" + c.type + "</td><td>" + disc + '</td><td class="money">' + money(c.min_spend) + "</td><td>" +
              fmtDateTime(c.starts_at) + "</td><td>" + fmtDateTime(c.expires_at) + '</td><td class="num">' + c.usage_count + '</td><td><span class="badge ' +
              (STATUS_BADGE[c.status] || "badge") + '">' + c.status + "</span></td><td>" +
              '<button class="secondary" data-edit="' + c.id + '">Edit</button> ' +
              '<button class="secondary" data-toggle="' + c.id + '" data-active="' + (c.active ? 0 : 1) + '">' + (c.active ? "Disable" : "Enable") + "</button></td></tr>";
          }).join("") + "</tbody></table></div>";
        el.querySelectorAll("[data-edit]").forEach(function (b) {
          var item = r.body.items.find(function (x) { return x.id == b.getAttribute("data-edit"); });
          b.onclick = function () { showForm(item); };
        });
        el.querySelectorAll("[data-toggle]").forEach(function (b) {
          b.onclick = function () {
            api("PATCH", "/api/manage/coupons/" + b.getAttribute("data-toggle") + "/active", { body: { active: b.getAttribute("data-active") === "1" } })
              .then(function () { toast("Coupon saved."); load(); });
          };
        });
      });
    }
    function toLocalInput(iso) {
      if (!iso) return "";
      return iso.slice(0, 16);
    }
    function showForm(item) {
      var box = document.getElementById("mcFormBox");
      var type = item ? item.type : "PERCENT";
      box.innerHTML = '<form id="mcForm" class="card"><h3>' + (item ? "Edit coupon" : "Add coupon") + "</h3>" +
        (item ? "" : '<div class="form-row"><label for="mc_code">Code</label><input id="mc_code"></div>' +
          '<div class="form-row"><label for="mc_type">Type</label><select id="mc_type"><option value="PERCENT">Percentage</option><option value="FIXED">Fixed amount</option></select></div>') +
        '<div class="form-row" id="mc_percent_row"><label for="mc_percent">Percent off</label><input id="mc_percent" value="' + esc(item && item.percent_off || "") + '"></div>' +
        '<div class="form-row" id="mc_max_row"><label for="mc_max">Maximum discount (optional)</label><input id="mc_max" value="' + esc(item && item.max_discount || "") + '"></div>' +
        '<div class="form-row" id="mc_amount_row"><label for="mc_amount">Amount off</label><input id="mc_amount" value="' + esc(item && item.amount_off || "") + '"></div>' +
        '<div class="form-row"><label for="mc_min">Minimum spend</label><input id="mc_min" value="' + esc(item ? item.min_spend : "0.00") + '"></div>' +
        '<div class="form-row"><label for="mc_start">Starts at</label><input id="mc_start" type="datetime-local" value="' + toLocalInput(item ? item.starts_at : "") + '"></div>' +
        '<div class="form-row"><label for="mc_end">Expires at</label><input id="mc_end" type="datetime-local" value="' + toLocalInput(item ? item.expires_at : "") + '"></div>' +
        '<p class="required-note">Times are in Asia/Bangkok (UTC+07:00).</p>' +
        '<div class="form-row"><label for="mc_peruser">Limit per user</label><input id="mc_peruser" value="' + esc(item ? item.per_user_limit : 1) + '"></div>' +
        '<div class="form-row"><label for="mc_total">Total limit (optional)</label><input id="mc_total" value="' + esc(item && item.total_limit || "") + '"></div>' +
        '<div id="mcError" class="field-error"></div>' +
        '<button type="submit">Save coupon</button> <button type="button" class="secondary" id="mcCancel">Cancel</button></form>';
      function syncType() {
        var t = item ? type : document.getElementById("mc_type").value;
        document.getElementById("mc_percent_row").style.display = t === "PERCENT" ? "" : "none";
        document.getElementById("mc_max_row").style.display = t === "PERCENT" ? "" : "none";
        document.getElementById("mc_amount_row").style.display = t === "FIXED" ? "" : "none";
      }
      syncType();
      if (!item) document.getElementById("mc_type").onchange = syncType;
      document.getElementById("mcCancel").onclick = function () { box.innerHTML = ""; };
      document.getElementById("mcForm").onsubmit = function (e) {
        e.preventDefault();
        var t = item ? type : document.getElementById("mc_type").value;
        var body = {
          min_spend: document.getElementById("mc_min").value,
          starts_at: document.getElementById("mc_start").value ? document.getElementById("mc_start").value + "+07:00" : undefined,
          expires_at: document.getElementById("mc_end").value ? document.getElementById("mc_end").value + "+07:00" : undefined,
          per_user_limit: Number(document.getElementById("mc_peruser").value),
          total_limit: document.getElementById("mc_total").value ? Number(document.getElementById("mc_total").value) : null,
        };
        if (t === "PERCENT") { body.percent_off = Number(document.getElementById("mc_percent").value); body.max_discount = document.getElementById("mc_max").value || null; }
        else { body.amount_off = document.getElementById("mc_amount").value; }
        var req;
        if (item) req = api("PUT", "/api/manage/coupons/" + item.id, { body: body });
        else { body.code = document.getElementById("mc_code").value; body.type = t; req = api("POST", "/api/manage/coupons", { body: body }); }
        req.then(function () { toast("Coupon saved."); box.innerHTML = ""; load(); })
          .catch(function (err) { document.getElementById("mcError").textContent = errMessage(err); });
      };
    }
  }

  // ---------- Manager: Reports ----------
  function renderManagerReports() {
    var p = qsParams();
    var tab = p.tab || "sales";
    var today = new Date();
    var weekAgo = new Date(today.getTime() - 6 * 86400000);
    function iso(d) { return d.toISOString().slice(0, 10); }
    mount('<h1>Reports</h1>' +
      '<div class="tabs" role="tablist">' +
      [["sales", "Sales"], ["top-products", "Top products"], ["coupons", "Coupons"], ["windows", "Window reports"]].map(function (t) {
        return '<button role="tab" aria-selected="' + (tab === t[0]) + '" data-tab="' + t[0] + '">' + t[1] + "</button>";
      }).join("") + "</div>" +
      '<div id="reportControls"></div><div id="reportBody">Loading&hellip;</div>');
    document.querySelectorAll("[data-tab]").forEach(function (b) { b.onclick = function () { navigate("/manager/reports?tab=" + b.getAttribute("data-tab")); }; });

    var controls = document.getElementById("reportControls");
    if (tab === "windows") {
      controls.innerHTML = '<form id="repForm" class="inline-form"><div><label for="rf_from">From (date and time)</label><input id="rf_from" type="datetime-local" value="' + (p.from || "") + '"></div>' +
        '<div><label for="rf_to">To (date and time)</label><input id="rf_to" type="datetime-local" value="' + (p.to || "") + '"></div>' +
        '<button type="submit">Show report</button></form>';
    } else {
      controls.innerHTML = '<form id="repForm" class="inline-form"><div><label for="rf_from">From</label><input id="rf_from" type="date" value="' + (p.from || iso(weekAgo)) + '"></div>' +
        '<div><label for="rf_to">To</label><input id="rf_to" type="date" value="' + (p.to || iso(today)) + '"></div>' +
        '<button type="submit">Show report</button>' + (tab !== "coupons" ? '<button type="button" id="exportCsv" class="secondary">Export CSV</button>' : "") + '</form>';
    }
    document.getElementById("repForm").onsubmit = function (e) {
      e.preventDefault();
      navigate("/manager/reports?tab=" + tab + "&from=" + encodeURIComponent(document.getElementById("rf_from").value) + "&to=" + encodeURIComponent(document.getElementById("rf_to").value));
    };
    load();
    function fromTo() {
      var from = document.getElementById("rf_from").value;
      var to = document.getElementById("rf_to").value;
      if (tab === "windows") return { from: from ? from + "+07:00" : "", to: to ? to + "+07:00" : "" };
      return { from: from || iso(weekAgo), to: to || iso(today) };
    }
    function load() {
      var ft = fromTo();
      var body = document.getElementById("reportBody");
      if (tab === "sales") {
        api("GET", "/api/manage/reports/sales", { qs: ft }).then(function (r) { renderSales(r.body); });
      } else if (tab === "top-products") {
        api("GET", "/api/manage/reports/top-products", { qs: ft }).then(function (r) { renderTop(r.body.items); });
      } else if (tab === "coupons") {
        api("GET", "/api/manage/reports/coupon-usage", { qs: ft }).then(function (r) { renderCoupons(r.body.items); });
      } else {
        api("GET", "/api/manage/reports/hourly", { qs: ft }).then(function (r) { renderWindows(r.body.items); });
      }
      var exp = document.getElementById("exportCsv");
      if (exp) exp.onclick = function () {
        var path = tab === "sales" ? "/api/manage/reports/sales.csv" : tab === "top-products" ? "/api/manage/reports/top-products.csv" : "/api/manage/reports/hourly.csv";
        api("GET", path, { qs: ft }).then(function (r) { downloadBlob(r.blob, r.filename); });
      };
      function renderSales(d) {
        if (d.order_count === 0 && d.daily.every(function (x) { return x.order_count === 0; })) { body.innerHTML = '<p class="empty-state">No data for the selected period.</p>'; return; }
        body.innerHTML = "<p>Orders: " + d.order_count + " &nbsp; Gross sales: " + money(d.gross_sales) + " &nbsp; VAT: " + money(d.vat_total) +
          " &nbsp; Shipping: " + money(d.shipping_total) + " &nbsp; Discounts: " + money(d.discount_total) + " &nbsp; Average order value: " + money(d.average_order_value) + "</p>" +
          '<div class="table-wrap"><table><thead><tr><th>Date</th><th class="num">Orders</th><th class="num">Gross sales</th><th class="num">VAT</th><th class="num">Shipping</th><th class="num">Discounts</th></tr></thead><tbody>' +
          d.daily.map(function (row) { return "<tr><td>" + fmtDate(row.date) + '</td><td class="num">' + row.order_count + '</td><td class="num money">' + money(row.gross_sales) +
            '</td><td class="num money">' + money(row.vat_total) + '</td><td class="num money">' + money(row.shipping_total) + '</td><td class="num money">' + money(row.discount_total) + "</td></tr>"; }).join("") +
          "</tbody></table></div>";
      }
      function renderTop(items) {
        if (items.length === 0) { body.innerHTML = '<p class="empty-state">No data for the selected period.</p>'; return; }
        body.innerHTML = '<div class="table-wrap"><table><thead><tr><th class="num">Rank</th><th>Product</th><th class="num">Quantity</th><th class="num">Revenue</th></tr></thead><tbody>' +
          items.map(function (it, i) { return '<tr><td class="num">' + (i + 1) + "</td><td>" + esc(it.name) + '</td><td class="num">' + it.quantity + '</td><td class="num money">' + money(it.revenue) + "</td></tr>"; }).join("") +
          "</tbody></table></div>";
      }
      function renderCoupons(items) {
        if (items.length === 0) { body.innerHTML = '<p class="empty-state">No data for the selected period.</p>'; return; }
        body.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Code</th><th class="num">Orders</th><th class="num">Total discount</th></tr></thead><tbody>' +
          items.map(function (it) { return "<tr><td>" + esc(it.code) + '</td><td class="num">' + it.order_count + '</td><td class="num money">' + money(it.discount_total) + "</td></tr>"; }).join("") +
          "</tbody></table></div>";
      }
      function renderWindows(items) {
        if (items.length === 0) { body.innerHTML = '<p class="empty-state">No data for the selected period.</p>'; return; }
        body.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Window</th><th class="num">Orders</th><th class="num">Gross sales</th><th class="num">VAT</th><th class="num">Shipping</th><th class="num">Discounts</th><th>Generated</th></tr></thead><tbody>' +
          items.map(function (it) { return "<tr><td>" + fmtDateTime(it.window_start) + " – " + fmtDateTime(it.window_end) + '</td><td class="num">' + it.order_count +
            '</td><td class="num money">' + money(it.gross_sales) + '</td><td class="num money">' + money(it.vat_total) + '</td><td class="num money">' + money(it.shipping_total) +
            '</td><td class="num money">' + money(it.discount_total) + "</td><td>" + fmtDateTime(it.generated_at) + "</td></tr>"; }).join("") +
          "</tbody></table></div>";
      }
    }
  }

  // ---------- Admin: Users ----------
  function renderAdminUsers() {
    var p = qsParams();
    mount('<h1>Users</h1><div id="auFilter"></div><div id="auBody">Loading&hellip;</div>');
    document.getElementById("auFilter").innerHTML = '<form id="auFilterForm" class="inline-form"><div><label for="au_q">Search</label>' +
      '<input id="au_q" placeholder="Search by username or name" value="' + esc(p.q || "") + '"></div>' +
      '<div><label for="au_role">Role</label><select id="au_role"><option value="">All roles</option>' +
      ["customer", "staff", "manager", "admin"].map(function (r) { return '<option value="' + r + '"' + (p.role === r ? " selected" : "") + ">" + r + "</option>"; }).join("") +
      "</select></div><button type=\"submit\">Apply filters</button></form>";
    document.getElementById("auFilterForm").onsubmit = function (e) {
      e.preventDefault();
      navigate("/admin/users" + buildQs({ q: document.getElementById("au_q").value, role: document.getElementById("au_role").value }));
    };
    load();
    function load() {
      api("GET", "/api/admin/users", { qs: { q: p.q, role: p.role, page: p.page } }).then(function (r) {
        var el = document.getElementById("auBody");
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (u) {
            var statusLabel = u.status === "LOCKED" ? '<span class="badge badge-danger">Locked</span>' : (u.temporarily_locked ? '<span class="badge badge-warn">Temporarily locked</span>' : '<span class="badge badge-ok">Active</span>');
            return "<tr><td>" + esc(u.username) + "</td><td>" + u.display_name + "</td><td>" + esc(u.role) + "</td><td>" + statusLabel + "</td><td>" + fmtDate(u.created_at) + "</td><td>" +
              (u.status === "LOCKED" || u.temporarily_locked ? '<button class="secondary" data-unlock="' + u.id + '">Unlock</button>' : '<button class="secondary" data-lock="' + u.id + '">Lock</button>') + " " +
              '<button class="secondary" data-reset="' + u.id + '" data-username="' + esc(u.username) + '">Reset password</button> ' +
              '<button class="secondary" data-role="' + u.id + '" data-current-role="' + u.role + '">Change role</button></td></tr>';
          }).join("") + "</tbody></table></div><div id=\"auModal\"></div>";
        el.querySelectorAll("[data-lock]").forEach(function (b) {
          b.onclick = function () {
            confirmDialog("Lock account", "Lock this account? The user will be signed out immediately.", "Lock").then(function (ok) {
              if (!ok) return;
              api("POST", "/api/admin/users/" + b.getAttribute("data-lock") + "/lock").then(function () { toast("User locked."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
            });
          };
        });
        el.querySelectorAll("[data-unlock]").forEach(function (b) {
          b.onclick = function () {
            confirmDialog("Unlock account", "Unlock this account?", "Unlock").then(function (ok) {
              if (!ok) return;
              api("POST", "/api/admin/users/" + b.getAttribute("data-unlock") + "/unlock").then(function () { toast("Account unlocked."); load(); }).catch(function (err) { toast(errMessage(err), "error"); });
            });
          };
        });
        el.querySelectorAll("[data-reset]").forEach(function (b) {
          b.onclick = function () {
            var uid = b.getAttribute("data-reset");
            var uname = b.getAttribute("data-username");
            confirmDialog("Reset password", "Reset the password for " + uname + "? A temporary password will be generated.", "Reset password").then(function (ok) {
              if (!ok) return;
              api("POST", "/api/admin/users/" + uid + "/reset-password").then(function (r2) {
                var box = document.getElementById("auModal");
                box.innerHTML = '<div class="dialog-overlay"><div class="dialog-box"><h2>Temporary password</h2>' +
                  "<p>Share this password with the user. It will not be shown again.</p>" +
                  '<p style="font-family:monospace;font-size:18px">' + esc(r2.body.temporary_password) + "</p>" +
                  '<div class="dialog-actions"><button id="closeTemp">Close</button></div></div></div>';
                document.getElementById("closeTemp").onclick = function () { box.innerHTML = ""; load(); };
              });
            });
          };
        });
        el.querySelectorAll("[data-role]").forEach(function (b) {
          b.onclick = function () {
            var uid = b.getAttribute("data-role");
            var box = document.getElementById("auModal");
            box.innerHTML = '<div class="dialog-overlay"><div class="dialog-box"><h2>Change role</h2><form id="roleForm">' +
              '<label for="roleSelect">Role</label><select id="roleSelect">' +
              ["customer", "staff", "manager", "admin"].map(function (r) { return '<option value="' + r + '"' + (r === b.getAttribute("data-current-role") ? " selected" : "") + ">" + r + "</option>"; }).join("") +
              '</select><div id="roleError" class="field-error"></div>' +
              '<div class="dialog-actions"><button type="button" class="secondary" id="roleCancel">Cancel</button><button type="submit">Save</button></div></form></div></div>';
            document.getElementById("roleCancel").onclick = function () { box.innerHTML = ""; };
            document.getElementById("roleForm").onsubmit = function (e) {
              e.preventDefault();
              api("PATCH", "/api/admin/users/" + uid + "/role", { body: { role: document.getElementById("roleSelect").value } })
                .then(function () { toast("Role updated."); box.innerHTML = ""; load(); })
                .catch(function (err) { document.getElementById("roleError").textContent = errMessage(err); });
            };
          };
        });
      });
    }
  }

  // ---------- Admin: Jobs ----------
  function renderAdminJobs() {
    mount('<h1>Jobs</h1><div id="jobsBody">Loading&hellip;</div>');
    load();
    function load() {
      api("GET", "/api/admin/jobs").then(function (r) {
        var el = document.getElementById("jobsBody");
        el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Job</th><th>Description</th><th>Schedule</th><th>Last run</th><th>Next run</th><th>Actions</th></tr></thead><tbody>' +
          r.body.items.map(function (j) {
            var last = j.last_run ? (j.last_run.status === "SUCCESS" ? '<span class="badge badge-ok">Success</span>' : j.last_run.status === "FAILED" ? '<span class="badge badge-danger">Failed</span>' : '<span class="badge badge-warn">Running</span>') + " " + fmtDateTime(j.last_run.started_at) : "Never";
            return "<tr><td>" + esc(j.name) + "</td><td>" + esc(j.description) + "</td><td>" + esc(j.schedule) + "</td><td>" + last + "</td><td>" + fmtDateTime(j.next_run_at) + "</td><td>" +
              '<button data-run="' + j.name + '">Run now</button> <a data-link href="/admin/jobs/' + j.name + '/history">View history</a></td></tr>';
          }).join("") + "</tbody></table></div><div id=\"jobModal\"></div>";
        el.querySelectorAll("[data-run]").forEach(function (b) {
          b.onclick = function () {
            var name = b.getAttribute("data-run");
            if (name === "hourly-sales-report") {
              var box = document.getElementById("jobModal");
              box.innerHTML = '<div class="dialog-overlay"><div class="dialog-box"><h2>Run report</h2><form id="runForm">' +
                '<label for="runFrom">From (optional)</label><input id="runFrom" type="datetime-local">' +
                '<label for="runTo">To (optional)</label><input id="runTo" type="datetime-local">' +
                '<p class="required-note">Leave empty to use the previous full hour.</p>' +
                '<div class="dialog-actions"><button type="button" class="secondary" id="runCancel">Cancel</button><button type="submit">Run report</button></div></form></div></div>';
              document.getElementById("runCancel").onclick = function () { box.innerHTML = ""; };
              document.getElementById("runForm").onsubmit = function (e) {
                e.preventDefault();
                var body = {};
                var f = document.getElementById("runFrom").value, t = document.getElementById("runTo").value;
                if (f) body.from = f + "+07:00";
                if (t) body.to = t + "+07:00";
                doRun(name, body, box);
              };
            } else {
              confirmDialog("Run now", "Run this job now?", "Run now").then(function (ok) { if (ok) doRun(name, {}, null); });
            }
          };
        });
      });
    }
    function doRun(name, body, box) {
      api("POST", "/api/admin/jobs/" + name + "/run", { body: body }).then(function (r) {
        if (box) box.innerHTML = "";
        toast("Job finished: " + JSON.stringify(r.body.summary));
        load();
      }).catch(function (err) { toast(errMessage(err), "error"); });
    }
  }
  function renderAdminJobHistory(params) {
    mount('<h1>Run history</h1><div id="historyBody">Loading&hellip;</div>');
    api("GET", "/api/admin/jobs/" + params.name + "/runs").then(function (r) {
      var el = document.getElementById("historyBody");
      if (r.body.items.length === 0) { el.innerHTML = '<p class="empty-state">No runs yet.</p>'; return; }
      el.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Started</th><th>Finished</th><th>Trigger</th><th>By</th><th>Status</th><th>Result</th></tr></thead><tbody>' +
        r.body.items.map(function (run) {
          return "<tr><td>" + fmtDateTime(run.started_at) + "</td><td>" + (run.finished_at ? fmtDateTime(run.finished_at) : "—") + "</td><td>" +
            (run.trigger === "MANUAL" ? "Manual" : "Scheduled") + "</td><td>" + esc(run.triggered_by) + "</td><td>" + run.status + "</td><td>" +
            (run.summary ? esc(JSON.stringify(run.summary)) : (run.error_message ? esc(run.error_message) : "")) + "</td></tr>";
        }).join("") + "</tbody></table></div>";
    });
  }

  // ---------- route table ----------
  route("/login", renderLogin, { public: true });
  route("/register", renderRegister, { public: true });
  route("/change-password", renderChangePassword);
  route("/profile", renderProfile);
  route("/products", renderProducts, { anon: true });
  route("/products/:id", renderProductDetail, { anon: true });
  route("/wishlist", renderWishlist, { roles: ["customer"] });
  route("/cart", renderCart, { roles: ["customer"] });
  route("/checkout", renderCheckout, { roles: ["customer"] });
  route("/orders", renderMyOrders, { roles: ["customer"] });
  route("/orders/:id", renderOrderDetail, { roles: ["customer"] });
  route("/orders/:id/confirmation", renderOrderConfirmation, { roles: ["customer"] });
  route("/staff/orders", renderStaffOrders, { roles: ["staff", "admin"] });
  route("/staff/inventory", renderStaffInventory, { roles: ["staff", "admin"] });
  route("/staff/inventory/:id/history", renderStaffInventoryHistory, { roles: ["staff", "admin"] });
  route("/staff/low-stock", renderStaffLowStock, { roles: ["staff", "admin"] });
  route("/manager/products", renderManagerProducts, { roles: ["manager", "admin"] });
  route("/manager/coupons", renderManagerCoupons, { roles: ["manager", "admin"] });
  route("/manager/reports", renderManagerReports, { roles: ["manager", "admin"] });
  route("/admin/users", renderAdminUsers, { roles: ["admin"] });
  route("/admin/jobs", renderAdminJobs, { roles: ["admin"] });
  route("/admin/jobs/:name/history", renderAdminJobHistory, { roles: ["admin"] });
  route("/", function () {
    if (state.user && state.user.role !== "customer") { navigate(currentHome()); return; }
    navigate("/products");
  }, { anon: true });

  // ---------- bootstrap ----------
  function boot() {
    var token = getToken();
    if (!token) { renderRoute(); return; }
    api("GET", "/api/me").then(function (r) {
      state.user = r.body;
      renderRoute();
    }).catch(function () {
      clearToken();
      renderRoute();
    });
  }
  boot();
})();
