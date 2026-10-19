"use strict";

const API = "/api/v1";
const $view = document.getElementById("view");

/* ---------- helpers ---------- */

// Every piece of user text goes through esc() before it reaches innerHTML.
const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const store = {
    get token() { try { return localStorage.getItem("token"); } catch { return null; } },
    set token(v) { try { v ? localStorage.setItem("token", v) : localStorage.removeItem("token"); } catch { /* private mode */ } },
};

function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast.t);
    toast.t = setTimeout(() => el.classList.remove("show"), 2600);
}

// Flatten DRF error payloads ({field: [msgs]} or {detail}) into readable lines.
function errorText(data) {
    if (!data) return "Something went wrong. Please try again.";
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    return Object.entries(data)
        .map(([k, v]) => `${k === "non_field_errors" ? "" : k + ": "}${[].concat(v).join(" ")}`)
        .join("\n");
}

async function api(path, { method = "GET", body, url } = {}) {
    const headers = { Accept: "application/json" };
    const isForm = body instanceof FormData; // browser sets the multipart boundary itself
    if (body && !isForm) headers["Content-Type"] = "application/json";
    if (store.token) headers.Authorization = `Token ${store.token}`;
    let res;
    try {
        res = await fetch(url || API + path, { method, headers, body: body ? (isForm ? body : JSON.stringify(body)) : undefined });
    } catch {
        throw new Error("Network problem. Check your connection.");
    }
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (res.status === 401 && store.token) { store.token = null; location.hash = "#/login"; }
    if (!res.ok) throw new Error(errorText(data));
    return data;
}

const loggedIn = () => !!store.token;
const needLogin = () => { toast("Please log in first"); location.hash = "#/login"; };

/* ---------- photos ---------- */

// Phone photos are often 5-10 MB; scale to 1280px JPEG before uploading.
async function shrink(file, max = 1280) {
    if (!file || !file.type.startsWith("image/")) return file;
    const bmp = await createImageBitmap(file).catch(() => null);
    if (!bmp) return file;
    const scale = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.82));
    return blob ? new File([blob], "photo.jpg", { type: "image/jpeg" }) : file;
}

// Image that shows a skeleton until it has loaded (or hides itself if it fails).
const photo = (url, cls) =>
    url ? `<div class="photo skeleton ${cls}"><img src="${esc(url)}" alt="" loading="lazy"
        onload="this.parentNode.classList.remove('skeleton')" onerror="this.parentNode.remove()"></div>` : "";

/* ---------- skeleton loaders ---------- */

const skCard = () => `
    <div class="card">
        <div class="skeleton sk-title"></div>
        <div class="skeleton sk-line w90"></div>
        <div class="skeleton sk-line w40"></div>
    </div>`;
const skeletons = (n = 4) => Array.from({ length: n }, skCard).join("");

const badge = (s) => `<span class="badge ${esc(s)}">${esc(s)}</span>`;
const when = (iso) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });

/* ---------- views ---------- */

const state = { status: "", category: "", search: "" };

async function viewHome() {
    $view.innerHTML = `
        <h2>Lost &amp; Found</h2>
        <input id="q" type="search" placeholder="Search items, places..." value="${esc(state.search)}">
        <div class="chips" id="chips">
            ${["", "lost", "found", "returned"]
                .map((s) => `<button class="chip ${state.status === s ? "active" : ""}" data-s="${s}">${s || "All"}</button>`)
                .join("")}
        </div>
        <select id="cat"><option value="">All categories</option></select>
        <div id="list">${skeletons()}</div>
        <div id="more"></div>`;

    const cat = document.getElementById("cat");
    api("/categories/").then((cats) => {
        const list = cats.results || cats;
        cat.innerHTML += list.map((c) => `<option value="${c.id}" ${String(c.id) === state.category ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    }).catch(() => {});

    let timer;
    document.getElementById("q").oninput = (e) => {
        state.search = e.target.value;
        clearTimeout(timer);
        timer = setTimeout(loadItems, 300);
    };
    document.getElementById("chips").onclick = (e) => {
        const b = e.target.closest("[data-s]");
        if (!b) return;
        state.status = b.dataset.s;
        document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === b));
        loadItems();
    };
    cat.onchange = () => { state.category = cat.value; loadItems(); };
    loadItems();
}

async function loadItems(pageUrl) {
    const list = document.getElementById("list");
    const more = document.getElementById("more");
    if (!list) return;
    if (!pageUrl) list.innerHTML = skeletons();
    more.innerHTML = "";
    const params = new URLSearchParams();
    if (state.status) params.set("status", state.status);
    if (state.category) params.set("category", state.category);
    if (state.search.trim()) params.set("search", state.search.trim());
    try {
        const data = await api(`/items/?${params}`, pageUrl ? { url: pageUrl } : {});
        const html = data.results.map(itemCard).join("");
        if (pageUrl) list.insertAdjacentHTML("beforeend", html);
        else list.innerHTML = html || `<div class="empty">No items found.</div>`;
        if (data.next) {
            more.innerHTML = `<button class="btn secondary" id="moreBtn">Load more</button>`;
            document.getElementById("moreBtn").onclick = () => loadItems(data.next);
        }
    } catch (e) {
        list.innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
}

const itemCard = (i) => `
    <a class="card" href="#/item/${i.id}">
        ${photo(i.image, "thumb")}
        <div class="row"><h3>${esc(i.title)}</h3>${badge(i.status)}</div>
        <p class="muted">${esc(i.location)}${i.category_name ? " · " + esc(i.category_name) : ""} · ${when(i.created_at)}</p>
        <p>${esc(i.description).slice(0, 110)}</p>
    </a>`;

async function viewItem(id) {
    $view.innerHTML = skeletons(1) + skeletons(1);
    let item;
    try { item = await api(`/items/${id}/`); }
    catch (e) { $view.innerHTML = `<div class="error">${esc(e.message)}</div>`; return; }

    let me = null;
    if (loggedIn()) me = await api("/auth/me/").catch(() => null);
    const mine = me && me.id === item.created_by;

    $view.innerHTML = `
        <a href="#/">&larr; Back</a>
        <div class="card" style="margin-top:10px">
            ${photo(item.image, "hero")}
            <div class="row"><h2 style="margin:0">${esc(item.title)}</h2>${badge(item.status)}</div>
            <p class="muted">${esc(item.location)}${item.category_name ? " · " + esc(item.category_name) : ""}</p>
            <p>${esc(item.description)}</p>
            <p class="muted">Posted by ${esc(item.created_by_name)} on ${when(item.created_at)}</p>
        </div>
        <div id="extra"></div>`;
    const extra = document.getElementById("extra");

    if (item.status === "returned") return;

    if (mine) {
        extra.innerHTML = `
            <button class="btn secondary" id="ret">Mark as returned</button>
            <h2 style="margin-top:20px">Claims</h2><div id="claims">${skeletons(2)}</div>`;
        document.getElementById("ret").onclick = async () => {
            if (!confirm("Close this item? Pending claims will be rejected.")) return;
            try { await api(`/items/${id}/mark-returned/`, { method: "POST" }); toast("Item closed"); viewItem(id); }
            catch (e) { toast(e.message); }
        };
        const data = await api(`/claims/?item=${id}`).catch(() => ({ results: [] }));
        document.getElementById("claims").innerHTML = data.results.map((c) => claimCard(c, "owner")).join("") || `<div class="empty">No claims yet.</div>`;
        bindClaimActions(() => viewItem(id));
    } else {
        extra.innerHTML = `
            <h2 style="margin-top:20px">This is mine</h2>
            <form id="claimForm">
                <div class="error" id="err" hidden></div>
                <label for="msg">Prove it's yours</label>
                <textarea id="msg" required minlength="10" placeholder="Describe something only the owner would know..."></textarea>
                <button class="btn">Submit claim</button>
            </form>`;
        document.getElementById("claimForm").onsubmit = async (e) => {
            e.preventDefault();
            if (!loggedIn()) return needLogin();
            await submit(e.target, async () => {
                await api("/claims/", { method: "POST", body: { item: Number(id), message: document.getElementById("msg").value } });
                toast("Claim sent");
                location.hash = "#/claims";
            });
        };
    }
}

function viewNew() {
    if (!loggedIn()) return needLogin();
    $view.innerHTML = `
        <h2>Post an item</h2>
        <form id="f">
            <div class="error" id="err" hidden></div>
            <label for="status">I...</label>
            <select id="status"><option value="lost">lost something</option><option value="found">found something</option></select>
            <label for="title">What is it?</label>
            <input id="title" required minlength="3" maxlength="200" placeholder="Black wallet">
            <label for="category">Category</label>
            <select id="category"><option value="">Other</option></select>
            <label for="location">Where?</label>
            <input id="location" required maxlength="200" placeholder="Library, 2nd floor">
            <label for="description">Details</label>
            <textarea id="description" required placeholder="Colour, brand, anything distinctive"></textarea>
            <label for="image">Photo (optional)</label>
            <input id="image" type="file" accept="image/jpeg,image/png,image/webp">
            <img id="preview" class="preview" alt="" hidden>
            <button class="btn">Post</button>
        </form>`;
    api("/categories/").then((cats) => {
        document.getElementById("category").innerHTML += (cats.results || cats).map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
    }).catch(() => {});
    const fileInput = document.getElementById("image");
    const preview = document.getElementById("preview");
    fileInput.onchange = () => {
        const f = fileInput.files[0];
        preview.hidden = !f;
        if (f) preview.src = URL.createObjectURL(f);
    };
    document.getElementById("f").onsubmit = (e) => {
        e.preventDefault();
        submit(e.target, async () => {
            const form = new FormData();
            ["status", "title", "location", "description"].forEach((k) => form.append(k, val(k)));
            if (val("category")) form.append("category", val("category"));
            if (fileInput.files[0]) form.append("image", await shrink(fileInput.files[0]));
            const item = await api("/items/", { method: "POST", body: form });
            toast("Posted");
            location.hash = `#/item/${item.id}`;
        });
    };
}

async function viewClaims() {
    if (!loggedIn()) return needLogin();
    let role = viewClaims.role || "claimant";
    $view.innerHTML = `
        <h2>Claims</h2>
        <div class="chips">
            <button class="chip ${role === "claimant" ? "active" : ""}" data-r="claimant">My claims</button>
            <button class="chip ${role === "owner" ? "active" : ""}" data-r="owner">On my items</button>
        </div>
        <div id="list">${skeletons(3)}</div>`;
    $view.querySelector(".chips").onclick = (e) => {
        const b = e.target.closest("[data-r]");
        if (b) { viewClaims.role = b.dataset.r; viewClaims(); }
    };
    try {
        const data = await api(`/claims/?role=${role}`);
        document.getElementById("list").innerHTML = data.results.map((c) => claimCard(c, role)).join("") || `<div class="empty">Nothing here yet.</div>`;
        bindClaimActions(viewClaims);
    } catch (e) {
        document.getElementById("list").innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
}

function claimCard(c, role) {
    const contact = c.contact
        ? `<div class="contact"><strong>${esc(c.contact.name)}</strong><br>${esc(c.contact.email)}<br>${esc(c.contact.phone)}</div>`
        : "";
    let actions = "";
    if (c.status === "pending" && role === "owner")
        actions = `<div class="actions"><button class="btn small" data-act="approve" data-id="${c.id}">Approve</button><button class="btn small danger" data-act="reject" data-id="${c.id}">Reject</button></div>`;
    if (c.status === "pending" && role === "claimant")
        actions = `<div class="actions"><button class="btn small secondary" data-act="withdraw" data-id="${c.id}">Withdraw</button></div>`;
    return `
        <div class="card">
            <div class="row"><h3><a href="#/item/${c.item}">${esc(c.item_title)}</a></h3>${badge(c.status)}</div>
            <p class="muted">${role === "owner" ? "From " + esc(c.claimant_name) : "Sent"} · ${when(c.created_at)}</p>
            <p>${esc(c.message)}</p>${contact}${actions}
        </div>`;
}

function bindClaimActions(reload) {
    $view.querySelectorAll("[data-act]").forEach((b) => {
        b.onclick = async () => {
            b.disabled = true;
            try {
                await api(`/claims/${b.dataset.id}/${b.dataset.act}/`, { method: "POST" });
                toast("Done");
                reload();
            } catch (e) { toast(e.message); b.disabled = false; }
        };
    });
}

function viewLogin() {
    $view.innerHTML = `
        <h2>Log in</h2>
        <form id="f">
            <div class="error" id="err" hidden></div>
            <label for="email">Email</label><input id="email" type="email" required autocomplete="email">
            <label for="password">Password</label><input id="password" type="password" required autocomplete="current-password">
            <button class="btn">Log in</button>
        </form>
        <p class="muted" style="text-align:center">No account? <a href="#/register">Sign up</a></p>`;
    document.getElementById("f").onsubmit = (e) => {
        e.preventDefault();
        submit(e.target, async () => {
            const d = await api("/auth/login/", { method: "POST", body: { email: val("email"), password: val("password") } });
            store.token = d.token;
            toast("Welcome back");
            location.hash = "#/";
        });
    };
}

function viewRegister() {
    $view.innerHTML = `
        <h2>Create account</h2>
        <form id="f">
            <div class="error" id="err" hidden></div>
            <label for="first_name">First name</label><input id="first_name" required maxlength="50" autocomplete="given-name">
            <label for="last_name">Last name</label><input id="last_name" required maxlength="50" autocomplete="family-name">
            <label for="email">Email</label><input id="email" type="email" required autocomplete="email">
            <label for="phone">Phone</label><input id="phone" type="tel" required placeholder="0781234567" autocomplete="tel">
            <label for="password">Password</label><input id="password" type="password" required minlength="8" autocomplete="new-password">
            <button class="btn">Sign up</button>
        </form>
        <p class="muted" style="text-align:center">Have an account? <a href="#/login">Log in</a></p>`;
    document.getElementById("f").onsubmit = (e) => {
        e.preventDefault();
        submit(e.target, async () => {
            const body = {};
            ["first_name", "last_name", "email", "phone", "password"].forEach((k) => (body[k] = val(k)));
            const d = await api("/auth/register/", { method: "POST", body });
            store.token = d.token;
            toast("Account created");
            location.hash = "#/";
        });
    };
}

async function viewMe() {
    if (!loggedIn()) return needLogin();
    $view.innerHTML = skeletons(2);
    try {
        const me = await api("/auth/me/");
        $view.innerHTML = `
            <h2>${esc(me.first_name)} ${esc(me.last_name)}</h2>
            <p class="muted">${esc(me.email)}</p>
            <form id="f">
                <div class="error" id="err" hidden></div>
                <label for="phone">Phone</label><input id="phone" type="tel" value="${esc(me.phone)}" required>
                <button class="btn">Save</button>
            </form>
            <p></p>
            <button class="btn secondary" id="out">Log out</button>`;
        document.getElementById("f").onsubmit = (e) => {
            e.preventDefault();
            submit(e.target, async () => {
                await api("/auth/me/", { method: "PATCH", body: { phone: val("phone") } });
                toast("Saved");
            });
        };
        document.getElementById("out").onclick = async () => {
            await api("/auth/logout/", { method: "POST" }).catch(() => {});
            store.token = null;
            location.hash = "#/login";
        };
    } catch (e) {
        $view.innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
}

/* ---------- forms & routing ---------- */

const val = (id) => document.getElementById(id).value;

// Disables the button while saving and shows API errors inside the form.
async function submit(form, work) {
    const btn = form.querySelector("button:not([type=button])");
    const err = form.querySelector("#err");
    err.hidden = true;
    btn.disabled = true;
    try { await work(); }
    catch (e) { err.textContent = e.message; err.hidden = false; err.scrollIntoView({ block: "nearest" }); }
    finally { btn.disabled = false; }
}

const routes = [
    [/^#\/?$/, viewHome, "home"],
    [/^#\/item\/(\d+)$/, viewItem, "home"],
    [/^#\/new$/, viewNew, "new"],
    [/^#\/claims$/, viewClaims, "claims"],
    [/^#\/me$/, viewMe, "me"],
    [/^#\/login$/, viewLogin, "me"],
    [/^#\/register$/, viewRegister, "me"],
];

function route() {
    const hash = location.hash || "#/";
    for (const [re, fn, tab] of routes) {
        const m = hash.match(re);
        if (!m) continue;
        document.querySelectorAll("#tabbar a").forEach((a) => a.classList.toggle("active", a.dataset.tab === tab));
        window.scrollTo(0, 0);
        fn(...m.slice(1));
        return;
    }
    location.hash = "#/";
}

window.addEventListener("hashchange", route);
route();
