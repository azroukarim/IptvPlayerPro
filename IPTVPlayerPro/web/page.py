# -*- coding: utf-8 -*-
"""HTML page served by the local IPTV Player Pro web interface."""

PAGE = u"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b0b12">
<title>IPTV Player Pro — Control Panel</title>
<style>
:root {
    --bg: #0b0b12;
    --bg2: #14141f;
    --card: #171723;
    --line: #2b2b3d;
    --red: #e42020;
    --red2: #9d1111;
    --text: #f5f5f7;
    --muted: #9b9bad;
    --green: #37c871;
    --shadow: 0 18px 50px rgba(0, 0, 0, .35);
}
* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
    margin: 0;
    background:
        radial-gradient(circle at 18% -10%, rgba(180, 24, 24, .28), transparent 46%),
        radial-gradient(circle at 96% 8%, rgba(70, 34, 120, .16), transparent 40%),
        var(--bg);
    color: var(--text);
    font-family: Tahoma, "Segoe UI", Arial, sans-serif;
    line-height: 1.55;
}
a { color: #ff7878; }
.wrap { width: 100%; max-width: 1120px; margin: 0 auto; padding: 26px 18px 50px; }
header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 18px; margin-bottom: 22px;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand img { display: block; height: 54px; width: auto; }
.brand-title { font-size: 20px; font-weight: 700; letter-spacing: .2px; }
.brand-sub { color: var(--muted); font-size: 12px; margin-top: 1px; }
.connection {
    display: inline-flex; align-items: center; gap: 8px;
    border: 1px solid var(--line); background: rgba(23, 23, 35, .8);
    border-radius: 999px; padding: 7px 12px; color: var(--muted); font-size: 12px;
}
.dot { width: 8px; height: 8px; border-radius: 50%; background: #777; box-shadow: 0 0 10px #777; }
.dot.online { background: var(--green); box-shadow: 0 0 12px rgba(55, 200, 113, .8); }
.hero {
    border: 1px solid var(--line); border-radius: 18px; padding: 20px;
    background: linear-gradient(135deg, rgba(67, 12, 12, .82), rgba(21, 21, 33, .92) 58%);
    box-shadow: var(--shadow); margin-bottom: 18px;
}
.hero-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.hero h2 { margin: 0; font-size: 17px; }
.hero-name { font-size: 23px; font-weight: 700; margin: 12px 0 4px; }
.hero-url { color: #d0d0da; font-size: 13px; word-break: break-all; direction: ltr; text-align: left; }
.hero-meta { color: var(--muted); font-size: 13px; margin-top: 8px; display: flex; gap: 14px; flex-wrap: wrap; }
.pill {
    display: inline-flex; align-items: center; gap: 5px; border-radius: 999px;
    padding: 3px 9px; font-size: 11px; border: 1px solid #484860;
    color: #dedee8; background: rgba(255, 255, 255, .04); vertical-align: middle;
}
.pill.active { color: #9df0bb; border-color: rgba(55, 200, 113, .45); background: rgba(55, 200, 113, .1); }
.pill.mag { color: #ffc9a1; border-color: rgba(255, 151, 79, .35); background: rgba(255, 151, 79, .08); }
.pill.m3u { color: #b8d7ff; border-color: rgba(97, 165, 255, .35); background: rgba(97, 165, 255, .08); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 18px; }
.card {
    background: linear-gradient(160deg, rgba(29, 29, 43, .96), rgba(18, 18, 28, .96));
    border: 1px solid var(--line); border-radius: 18px; padding: 19px;
    box-shadow: var(--shadow);
}
.card h2 { margin: 0 0 4px; font-size: 17px; }
.card .sub { margin: 0 0 16px; color: var(--muted); font-size: 12px; }
label { display: block; font-size: 13px; color: #cfcfdb; margin: 11px 0 5px; }
label .opt { color: var(--muted); font-weight: normal; font-size: 11px; }
input[type=text], input[type=url], input[type=password] {
    width: 100%; border: 1px solid #3a3a50; background: #101019; color: var(--text);
    border-radius: 10px; padding: 10px 11px; font: inherit; font-size: 13px;
    outline: none; transition: border-color .15s, box-shadow .15s;
}
input[dir=ltr] { direction: ltr; text-align: left; }
input:focus { border-color: var(--red); box-shadow: 0 0 0 3px rgba(228, 32, 32, .13); }
.check { display: flex; align-items: center; gap: 8px; color: #cfcfdb; margin-top: 13px; font-size: 13px; }
.check input { accent-color: var(--red); width: 16px; height: 16px; }
.btn {
    border: 1px solid transparent; border-radius: 10px; padding: 9px 14px;
    font: inherit; font-size: 13px; font-weight: 700; color: #fff; cursor: pointer;
    background: #2a2a3d; transition: filter .15s, opacity .15s, border-color .15s;
}
.btn:hover { filter: brightness(1.12); }
.btn:disabled { opacity: .5; cursor: wait; }
.btn.primary { background: linear-gradient(135deg, var(--red), var(--red2)); box-shadow: 0 8px 20px rgba(228, 32, 32, .18); }
.btn.small { padding: 6px 10px; font-size: 12px; border-radius: 8px; }
.btn.ghost { background: transparent; border-color: #3c3c53; color: #dedee8; }
.btn.danger { background: rgba(189, 28, 28, .14); border-color: rgba(228, 32, 32, .4); color: #ff9d9d; }
.form-actions { display: flex; align-items: center; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.hint { color: var(--muted); font-size: 11px; margin: 12px 0 0; }
.sources-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 24px 0 12px; }
.sources-head h2 { margin: 0; font-size: 17px; }
.sources-head .count { color: var(--muted); font-size: 12px; }
.sources { display: grid; gap: 10px; }
.source {
    display: flex; align-items: center; justify-content: space-between; gap: 14px;
    border: 1px solid var(--line); border-radius: 14px; padding: 13px 15px;
    background: rgba(23, 23, 35, .8);
}
.source.is-active { border-color: rgba(228, 32, 32, .55); box-shadow: inset 3px 0 0 var(--red); }
.source-main { min-width: 0; flex: 1; }
.source-title { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; font-size: 14px; font-weight: 700; }
.source-url { color: #b6b6c6; font-size: 12px; margin-top: 5px; word-break: break-all; direction: ltr; text-align: left; }
.source-meta { color: var(--muted); font-size: 11px; margin-top: 5px; display: flex; gap: 12px; flex-wrap: wrap; }
.source-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.empty { text-align: center; color: var(--muted); border: 1px dashed #3a3a50; border-radius: 14px; padding: 28px 16px; font-size: 13px; }
.toast {
    position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%) translateY(20px);
    background: #202032; border: 1px solid #3d3d55; color: #f4f4f7; padding: 10px 16px;
    border-radius: 10px; font-size: 13px; opacity: 0; pointer-events: none;
    transition: opacity .2s, transform .2s; z-index: 10; max-width: calc(100vw - 32px);
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.toast.error { border-color: rgba(228, 32, 32, .6); color: #ffb3b3; }
footer { margin-top: 28px; color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
footer code { color: #d8d8e2; direction: ltr; }
@media (max-width: 640px) {
    .wrap { padding-top: 16px; }
    header { align-items: flex-start; flex-direction: column; }
    .brand img { height: 42px; }
    .source { align-items: flex-start; flex-direction: column; }
    .source-actions { justify-content: flex-start; }
    .hero-name { font-size: 19px; }
}
</style>
</head>
<body>
<div class="wrap">
    <header>
        <div class="brand">
            <img src="logo.png" alt="IPTV Player Pro" onerror="this.style.display='none'">
            <div>
                <div class="brand-title">IPTV Player Pro</div>
                <div class="brand-sub">Manage sources over your local network</div>
            </div>
        </div>
        <div class="connection"><span id="dot" class="dot"></span><span id="serverState">Connecting...</span></div>
    </header>

    <section class="hero">
        <div class="hero-top">
            <h2>Active source</h2>
            <span id="activeKind" class="pill" style="display:none"></span>
        </div>
        <div id="activeInfo" class="hero-name">No active source yet</div>
        <div id="activeUrl" class="hero-url"></div>
        <div id="activeMeta" class="hero-meta"></div>
    </section>

    <div class="grid">
        <form id="m3uForm" class="card" data-type="m3u" autocomplete="off">
            <h2>Add an M3U playlist</h2>
            <p class="sub">Add an M3U/M3U8 link to make it available inside the plugin.</p>
            <label for="m3uName">Playlist name <span class="opt">(optional)</span></label>
            <input id="m3uName" name="name" type="text" maxlength="80" placeholder="e.g. Main channels">
            <label for="m3uUrl">M3U URL</label>
            <input id="m3uUrl" name="url" type="url" dir="ltr" maxlength="2000" placeholder="http://example.com/playlist.m3u" required>
            <label for="m3uEpg">EPG URL <span class="opt">(optional)</span></label>
            <input id="m3uEpg" name="epg_url" type="url" dir="ltr" maxlength="2000" placeholder="http://example.com/xmltv.php">
            <label for="m3uUa">User-Agent <span class="opt">(optional)</span></label>
            <input id="m3uUa" name="ua" type="text" dir="ltr" maxlength="300" placeholder="VLC/3.0">
            <label class="check"><input name="activate" type="checkbox" checked> Activate this source after adding</label>
            <div class="form-actions">
                <button class="btn primary" type="submit">Add / update playlist</button>
            </div>
            <p class="hint">If the URL already exists, its details and cache will be refreshed. Leave the EPG field empty to read the guide address from the playlist or derive it from an Xtream link.</p>
        </form>

        <form id="magForm" class="card" data-type="mag" autocomplete="off">
            <h2>Add a MAG / Stalker portal</h2>
            <p class="sub">Add the portal URL and the MAC address registered with your provider.</p>
            <label for="magName">Portal name <span class="opt">(optional)</span></label>
            <input id="magName" name="name" type="text" maxlength="80" placeholder="e.g. Home portal">
            <label for="magUrl">Portal URL</label>
            <input id="magUrl" name="url" type="url" dir="ltr" maxlength="2000" placeholder="http://example.com:8080" required>
            <label for="magMac">MAC address</label>
            <input id="magMac" name="mac" type="text" dir="ltr" maxlength="17" placeholder="00:1A:79:12:34:56" required>
            <label for="magEpg">EPG URL <span class="opt">(optional)</span></label>
            <input id="magEpg" name="epg_url" type="url" dir="ltr" maxlength="2000" placeholder="http://example.com/xmltv.php">
            <label for="magUa">User-Agent <span class="opt">(optional)</span></label>
            <input id="magUa" name="ua" type="text" dir="ltr" maxlength="300" placeholder="MAG254">
            <label class="check"><input name="activate" type="checkbox" checked> Activate this source after adding</label>
            <div class="form-actions">
                <button class="btn primary" type="submit">Add / update portal</button>
            </div>
            <p class="hint">The MAC must be registered and active with your provider. Serial and Device ID are generated automatically.</p>
        </form>
    </div>

    <div class="sources-head">
        <h2>Saved sources <span id="sourceCount" class="count"></span></h2>
        <button id="reload" class="btn ghost small" type="button">Refresh</button>
    </div>
    <div id="sources" class="sources"></div>

    <footer>
        <span>Address: <code id="address">—</code></span>
        <span>Version: <code id="version">—</code></span>
    </footer>
</div>

<div id="toast" class="toast"></div>

<script>
(function () {
    "use strict";

    var state = { sources: [] };
    var toastTimer = null;

    function $(id) { return document.getElementById(id); }

    function esc(value) {
        return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char];
        });
    }

    function timeText(timestamp) {
        if (!timestamp) { return ""; }
        try { return new Date(timestamp * 1000).toLocaleString("en-GB"); }
        catch (error) { return String(timestamp); }
    }

    function statusText(source) {
        if (source.status === "active") { return "Active"; }
        if (source.status === "error") { return "Error"; }
        if (source.status === "expired") { return "Expired"; }
        if (source.status === "loaded") { return "Ready"; }
        return "Not loaded";
    }

    function countText(value, singular, plural) {
        return value + " " + (value === 1 ? singular : plural);
    }

    function toast(message, isError) {
        var box = $("toast");
        box.textContent = message;
        box.className = "toast show" + (isError ? " error" : "");
        if (toastTimer) { clearTimeout(toastTimer); }
        toastTimer = setTimeout(function () { box.className = "toast"; }, 4200);
    }

    function postHeaders() {
        return {"Content-Type": "application/json", "X-IPTVPro": "1"};
    }

    async function api(path, options) {
        var response = await fetch(path, options || {});
        var data = {};
        try { data = await response.json(); } catch (error) { data = {}; }
        if (!response.ok || data.ok === false) {
            throw new Error(data.error || ("HTTP " + response.status));
        }
        return data;
    }

    function sourceMeta(source) {
        var parts = [];
        if (source.type === "mag" && source.mac) { parts.push("MAC: " + source.mac); }
        if (source.expires) { parts.push("Expires: " + source.expires); }
        if (source.channels) { parts.push(countText(source.channels, "channel", "channels")); }
        if (source.vod) { parts.push(countText(source.vod, "movie", "movies")); }
        if (source.series) { parts.push(countText(source.series, "series", "series")); }
        if (source.updated) { parts.push("Last update: " + timeText(source.updated)); }
        return parts.join("  •  ");
    }

    function renderActive() {
        var active = null;
        for (var i = 0; i < state.sources.length; i++) {
            if (state.sources[i].active) { active = state.sources[i]; break; }
        }
        var kind = $("activeKind");
        if (!active) {
            $("activeInfo").textContent = "No active source yet";
            $("activeUrl").textContent = "";
            $("activeMeta").textContent = "Add a source using the forms below.";
            kind.style.display = "none";
            return;
        }
        kind.style.display = "";
        kind.className = "pill " + (active.type === "mag" ? "mag" : "m3u");
        kind.textContent = active.type === "mag" ? "MAG portal" : "M3U playlist";
        $("activeInfo").textContent = active.name || active.id;
        $("activeUrl").textContent = active.type === "mag"
            ? (active.mac + "  —  " + active.url)
            : active.url;
        $("activeMeta").textContent = sourceMeta(active) || statusText(active);
    }

    function renderSources() {
        var list = $("sources");
        $("sourceCount").textContent = "(" + state.sources.length + ")";
        if (!state.sources.length) {
            list.innerHTML = '<div class="empty">No saved sources yet. Add an M3U playlist or a MAG portal above.</div>';
            return;
        }
        var html = [];
        for (var i = 0; i < state.sources.length; i++) {
            var source = state.sources[i];
            var kindClass = source.type === "mag" ? "mag" : "m3u";
            var kindName = source.type === "mag" ? "MAG" : "M3U";
            var activePill = source.active ? '<span class="pill active">Active</span>' : "";
            var activateButton = source.active ? "" :
                '<button class="btn small ghost" type="button" data-action="activate" data-id="' + esc(source.id) + '">Activate</button>';
            var displayUrl = source.type === "mag"
                ? (esc(source.mac) + "  —  " + esc(source.url))
                : esc(source.url);
            html.push(
                '<article class="source' + (source.active ? " is-active" : "") + '">' +
                    '<div class="source-main">' +
                        '<div class="source-title">' + esc(source.name || source.id) +
                            ' <span class="pill ' + kindClass + '">' + kindName + '</span>' +
                            ' <span class="pill">' + esc(statusText(source)) + '</span>' + activePill +
                        '</div>' +
                        '<div class="source-url">' + displayUrl + '</div>' +
                        '<div class="source-meta">' + esc(sourceMeta(source)) + '</div>' +
                    '</div>' +
                    '<div class="source-actions">' +
                        activateButton +
                        '<button class="btn small ghost" type="button" data-action="refresh" data-id="' + esc(source.id) + '">Refresh</button>' +
                        '<button class="btn small danger" type="button" data-action="delete" data-id="' + esc(source.id) + '">Delete</button>' +
                    '</div>' +
                '</article>'
            );
        }
        list.innerHTML = html.join("");
    }

    function renderState(data) {
        state = data;
        $("dot").className = "dot online";
        $("serverState").textContent = "Connected";
        $("version").textContent = "v" + (data.version || "—");
        $("address").textContent = (data.urls && data.urls.length) ? data.urls[0] : "—";
        renderActive();
        renderSources();
    }

    async function loadState(showError) {
        try {
            var data = await api("api/state");
            renderState(data);
        } catch (error) {
            $("dot").className = "dot";
            $("serverState").textContent = "Offline";
            if (showError) { toast(error.message, true); }
        }
    }

    async function doAction(action, id, button) {
        if (action === "delete" && !confirm("Delete this source permanently?")) { return; }
        button.disabled = true;
        try {
            var data = await api("api/" + action, {
                method: "POST",
                headers: postHeaders(),
                body: JSON.stringify({id: id})
            });
            renderState(data.state);
            toast(action === "delete" ? "Source deleted" :
                  action === "activate" ? "Source activated" : "Source data updated");
        } catch (error) {
            toast(error.message, true);
            await loadState(false);
        } finally {
            button.disabled = false;
        }
    }

    function actionButton(node) {
        while (node && node !== document) {
            if (node.tagName === "BUTTON" && node.getAttribute("data-action")) { return node; }
            node = node.parentNode;
        }
        return null;
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest ? event.target.closest("button[data-action]") : actionButton(event.target);
        if (!button) { return; }
        doAction(button.getAttribute("data-action"), button.getAttribute("data-id"), button);
    });

    function formData(form) {
        var data = {type: form.getAttribute("data-type")};
        var elements = form.elements;
        for (var i = 0; i < elements.length; i++) {
            var element = elements[i];
            if (!element.name) { continue; }
            if (element.type === "checkbox") {
                data[element.name] = element.checked ? 1 : 0;
            } else {
                data[element.name] = String(element.value || "").trim();
            }
        }
        return data;
    }

    function bindForm(id) {
        var form = $(id);
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            var button = form.querySelector('button[type="submit"]');
            button.disabled = true;
            try {
                var result = await api("api/source", {
                    method: "POST",
                    headers: postHeaders(),
                    body: JSON.stringify(formData(form))
                });
                renderState(result.state);
                toast(result.updated ? "Source updated" : "Source added");
                form.reset();
            } catch (error) {
                toast(error.message, true);
            } finally {
                button.disabled = false;
            }
        });
    }

    $("reload").addEventListener("click", function () { loadState(true); });
    bindForm("m3uForm");
    bindForm("magForm");
    loadState(false);
})();
</script>
</body>
</html>
"""
