/* ═══ STATE ═══ */
let timelines = [];
let videos = [];
let timelineCounter = 0;
let outputPath = null;
let exportHistory = [];
const CLIP_COLORS = ["#3b82f6","#8b5cf6","#06b6d4","#f59e0b","#ef4444","#22c55e","#ec4899","#f97316"];

/* ═══ THEME ═══ */
function initTheme() {
    const saved = localStorage.getItem("theme") || "dark";
    document.body.classList.toggle("light", saved === "light");
    document.getElementById("themeToggle").addEventListener("click", () => {
        document.body.classList.toggle("light");
        localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark");
    });
}

/* ═══ ACCENT COLOR ═══ */
function initAccent() {
    const saved = localStorage.getItem("accent") || "#3b82f6";
    setAccent(saved);
    const picker = document.getElementById("accentPicker");
    picker.value = saved;
    document.getElementById("accentBtn").addEventListener("click", () => picker.click());
    picker.addEventListener("input", e => { setAccent(e.target.value); localStorage.setItem("accent", e.target.value); });
}
function setAccent(color) {
    document.documentElement.style.setProperty("--accent", color);
    document.documentElement.style.setProperty("--accent-hover", color);
    document.documentElement.style.setProperty("--accent-soft", color + "1a");
}

/* ═══ FULLSCREEN ═══ */
function initFullscreen() {
    document.getElementById("fullscreenBtn").addEventListener("click", toggleFullscreen);
    document.addEventListener("keydown", e => { if (e.key === "F11") { e.preventDefault(); toggleFullscreen(); } });
}
function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen();
}

/* ═══ PAGE NAV ═══ */
function initNav() {
    document.querySelectorAll(".rail-btn[data-page]").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".rail-btn[data-page]").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
            const pg = document.getElementById("page" + btn.dataset.page.charAt(0).toUpperCase() + btn.dataset.page.slice(1));
            if (pg) pg.classList.add("active");
            if (btn.dataset.page === "history") renderHistory();
        });
    });
    document.addEventListener("keydown", e => {
        if (e.altKey && e.key === "1") document.querySelector('[data-page="editor"]').click();
        if (e.altKey && e.key === "2") document.querySelector('[data-page="history"]').click();
    });
}

/* ═══ RESIZABLE SIDEBAR ═══ */
function initSidebarResize() {
    const handle = document.getElementById("sidebarResize");
    const sidebar = document.getElementById("sidebar");
    handle.addEventListener("mousedown", e => {
        const startX = e.clientX, startW = sidebar.offsetWidth;
        handle.classList.add("active");
        const onMove = e2 => { sidebar.style.width = Math.min(Math.max(startW + (e2.clientX - startX), 220), 500) + "px"; };
        const onUp = () => { handle.classList.remove("active"); document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });
}

/* ═══ TOOLTIP ═══ */
let tooltipEl = null;
function initTooltip() {
    tooltipEl = document.createElement("div");
    tooltipEl.className = "thumb-tooltip";
    document.body.appendChild(tooltipEl);
}
function showTooltip(e, thumbSrc) {
    if (!thumbSrc || !tooltipEl) return;
    tooltipEl.innerHTML = `<img src="${thumbSrc}">`;
    tooltipEl.classList.add("show");
    positionTooltip(e);
}
function moveTooltip(e) { positionTooltip(e); }
function hideTooltip() { if (tooltipEl) tooltipEl.classList.remove("show"); }
function positionTooltip(e) {
    if (!tooltipEl) return;
    let x = e.clientX + 16, y = e.clientY - 60;
    if (x + 250 > window.innerWidth) x = e.clientX - 260;
    if (y < 10) y = 10;
    tooltipEl.style.left = x + "px"; tooltipEl.style.top = y + "px";
}

/* ═══ FOLDER PICKERS ═══ */
function selectSource() {
    document.getElementById("loadingBar").classList.add("show");
    document.getElementById("loadingFill").style.width = "0%";
    eel.choose_source()(result => {
        document.getElementById("loadingBar").classList.remove("show");
        if (!result) { showToast("Source selection cancelled", true); return; }
        videos = result.files;
        document.getElementById("srcLabel").textContent = result.path;
        displayVideos();
        showToast(`Loaded ${videos.length} video(s)`);
    });
}
function selectDestination() {
    eel.choose_destination()(dst => {
        if (!dst) { showToast("Destination not selected", true); return; }
        outputPath = dst;
        document.getElementById("dstLabel").textContent = dst;
    });
}

/* ═══ EEL: Loading progress ═══ */
eel.expose(source_loading);
function source_loading(count) {
    document.getElementById("loadingBar").classList.add("show");
    document.getElementById("loadingFill").style.width = "0%";
    document.getElementById("videoList").innerHTML = `<div class="empty-hint">Loading ${count} video(s)…</div>`;
}
eel.expose(source_progress);
function source_progress(done, total, name) {
    document.getElementById("loadingFill").style.width = (done / total * 100) + "%";
    if (done === total) setTimeout(() => document.getElementById("loadingBar").classList.remove("show"), 500);
}

/* ═══ EXPLORER DROP ═══ */
function handleExplorerDragOver(e) { e.preventDefault(); e.currentTarget.classList.add("drag-hover"); }
function handleExplorerDrop(e) {
    e.preventDefault(); e.currentTarget.classList.remove("drag-hover");
    showToast("Use 'Open folder' to load videos (browser security limits direct file access)", true);
}

/* ═══ VIDEO LIBRARY ═══ */
function displayVideos() {
    const list = document.getElementById("videoList");
    if (!videos.length) { list.innerHTML = '<div class="empty-hint">No video files found</div>'; return; }
    list.innerHTML = videos.map((v, i) => `
        <div class="vid-item" draggable="true" data-idx="${i}">
            <div class="vid-thumb"
                 onmouseenter="showTooltip(event, videos[${i}].thumbnail)"
                 onmousemove="moveTooltip(event)" onmouseleave="hideTooltip()">
                ${v.thumbnail ? `<img src="${v.thumbnail}" alt="" loading="lazy">` :
                `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l8 5-8 5V6z"/></svg>`}
            </div>
            <div class="vid-meta">
                <div class="vid-name">${esc(v.name)}</div>
                <div class="vid-detail">${esc(v.size)}  ·  ${esc(v.durationText||'—')}${v.codec?'  ·  '+esc(v.codec):''}</div>
            </div>
            <button class="add-all-btn" onclick="event.stopPropagation();addVideoToAllTimelines(${i})" title="Add to all timelines">+</button>
        </div>
    `).join("");
    list.querySelectorAll(".vid-item").forEach(el => {
        el.addEventListener("dragstart", e => {
            e.dataTransfer.setData("text/plain", JSON.stringify({ type: "lib", idx: parseInt(el.dataset.idx) }));
        });
    });
}



/* ═══ ADD TO ALL ═══ */
function addVideoToAllTimelines(vidIdx) {
    const v = videos[vidIdx];
    if (!v || !timelines.length) { showToast("No timelines available", true); return; }
    let added = 0;
    timelines.forEach(tl => {
        if (!tl.videos.some(x => x.path === v.path)) {
            tl.videos.push({ name:v.name, path:v.path, duration:v.duration||0, durationText:v.durationText||"—", color:null, thumbnail:v.thumbnail });
            added++;
        }
    });
    if (added > 0) { renderTimelines(); showToast(`Added "${v.name}" to ${added} timeline(s)`); }
    else showToast(`"${v.name}" already in all timelines`, true);
}

/* ═══ TIMELINE CRUD ═══ */
function addTimeline() { timelineCounter++; timelines.push({id:`tl_${timelineCounter}`,name:`Timeline ${timelineCounter}`,videos:[]}); renderTimelines(); }
function removeTimeline(id) { timelines = timelines.filter(t => t.id !== id); renderTimelines(); }
function updateTimelineName(id, name) { const tl = timelines.find(t => t.id === id); if (tl) tl.name = name; }
function removeVideoFromTimeline(tlId, idx) { const tl = timelines.find(t => t.id === tlId); if (tl) { tl.videos.splice(idx,1); renderTimelines(); } }

/* ═══ CLIP COLOR ═══ */
function cycleClipColor(tlId, idx) {
    const tl = timelines.find(t => t.id === tlId); if (!tl) return;
    const clip = tl.videos[idx];
    const cur = CLIP_COLORS.indexOf(clip.color);
    clip.color = CLIP_COLORS[(cur + 1) % CLIP_COLORS.length];
    renderTimelines();
}

/* ═══ RENDER TIMELINES ═══ */
function renderTimelines() {
    const c = document.getElementById("timelinesContainer");
    if (!timelines.length) { c.innerHTML = '<div class="empty-hint">Click "+ Add timeline" to get started</div>'; return; }
    c.innerHTML = timelines.map(tl => {
        const totalDur = tl.videos.reduce((s,v) => s + (v.duration||0), 0);
        return `
        <div class="tl-card" data-id="${tl.id}">
            <div class="tl-head">
                <div class="tl-head-left">
                    <span class="tl-grip">⠿</span>
                    <input class="tl-name" value="${esc(tl.name)}" onchange="updateTimelineName('${tl.id}',this.value)">
                    ${totalDur > 0 ? `<span class="tl-dur">${formatDuration(totalDur)}</span>` : ''}
                </div>
                <button class="tl-remove" onclick="removeTimeline('${tl.id}')">✕</button>
            </div>
            ${tl.videos.length === 0
                ? `<div class="tl-empty" data-id="${tl.id}" ondrop="handleDrop(event)" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">Drag videos here</div>`
                : `<div class="tl-track" data-id="${tl.id}" ondrop="handleDrop(event)" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">
                    ${tl.videos.map((v,i) => {
                        const pct = totalDur > 0 ? Math.max((v.duration||1)/totalDur*100, 5) : (100/tl.videos.length);
                        const bg = v.color || CLIP_COLORS[i % CLIP_COLORS.length];
                        return `<div class="tl-clip" style="width:${pct}%;background:${bg}" draggable="true"
                                    data-tl="${tl.id}" data-idx="${i}"
                                    ondragstart="handleClipDragStart(event)"
                                    ondragover="event.preventDefault()" ondrop="handleClipDrop(event)"
                                    ondblclick="cycleClipColor('${tl.id}',${i})"
                                    onmouseenter="showTooltip(event,videos.find(x=>x.path==='${v.path.replace(/\\/g,'\\\\').replace(/'/g,"\\'")}')?.thumbnail)"
                                    onmousemove="moveTooltip(event)" onmouseleave="hideTooltip()"
                                    title="Double-click to change color">
                            <button class="clip-x" onclick="event.stopPropagation();removeVideoFromTimeline('${tl.id}',${i})">✕</button>
                            <span class="clip-dur">${esc(v.durationText||'')}</span>
                            <span class="clip-name">${esc(v.name)}</span>
                        </div>`;
                    }).join("")}
                  </div>`}
        </div>`;
    }).join("");
}

/* ═══ DRAG & DROP ═══ */
function handleDragOver(e) { e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
function handleDragLeave(e) { e.currentTarget.classList.remove("drag-over"); }
function handleDrop(e) {
    e.preventDefault(); e.currentTarget.classList.remove("drag-over");
    const data = JSON.parse(e.dataTransfer.getData("text/plain"));
    const targetId = e.currentTarget.dataset.id;
    if (data.type === "lib") {
        const v = videos[data.idx]; if (!v) return;
        const tl = timelines.find(t => t.id === targetId);
        if (!tl || tl.videos.some(x => x.path === v.path)) return;
        tl.videos.push({name:v.name,path:v.path,duration:v.duration||0,durationText:v.durationText||"—",color:null,thumbnail:v.thumbnail});
        renderTimelines();
    } else if (data.type === "clip") {
        const src = timelines.find(t => t.id === data.tl);
        const dst = timelines.find(t => t.id === targetId);
        if (!src || !dst) return;
        dst.videos.push(src.videos.splice(data.idx,1)[0]); renderTimelines();
    }
}
function handleClipDragStart(e) { e.dataTransfer.setData("text/plain", JSON.stringify({type:"clip",tl:e.target.dataset.tl,idx:parseInt(e.target.dataset.idx)})); }
function handleClipDrop(e) {
    e.preventDefault(); e.stopPropagation();
    const data = JSON.parse(e.dataTransfer.getData("text/plain"));
    const el = e.target.closest(".tl-clip");
    const tgtTl = el?.dataset.tl, tgtIdx = parseInt(el?.dataset.idx);
    if (data.type === "lib") {
        const v = videos[data.idx]; if (!v) return;
        const tl = timelines.find(t => t.id === tgtTl);
        if (!tl || tl.videos.some(x => x.path === v.path)) return;
        tl.videos.splice(tgtIdx,0,{name:v.name,path:v.path,duration:v.duration||0,durationText:v.durationText||"—",color:null,thumbnail:v.thumbnail});
    } else if (data.type === "clip") {
        const s = timelines.find(t => t.id === data.tl), d = timelines.find(t => t.id === tgtTl);
        if (!s || !d) return;
        const clip = s.videos.splice(data.idx,1)[0];
        let ins = tgtIdx; if (data.tl === tgtTl && data.idx < tgtIdx) ins--;
        d.videos.splice(ins,0,clip);
    }
    renderTimelines();
}

/* ═══ EXPORT ═══ */
function exportTimelines() {
    if (!outputPath) { showToast("Pick a destination first", true); return; }
    const used = timelines.filter(t => t.videos.length);
    if (!used.length) { showToast("No videos in timelines", true); return; }
    document.getElementById("exportBtn").disabled = true;
    document.getElementById("progressBar").classList.add("show");
    eel.export_timelines(JSON.stringify(used), outputPath, document.getElementById("fmtSelect").value, document.getElementById("qualitySelect").value)(result => {
        document.getElementById("exportBtn").disabled = false;
        document.getElementById("progressBar").classList.remove("show");
        document.getElementById("progFill").style.width = "0%";
        document.getElementById("progLabel").textContent = "";
        document.getElementById("progPct").textContent = "";
        document.getElementById("progEta").textContent = "";
        showToast(result.msg, !result.ok);
        // Notification sound
        try { document.getElementById("notifSound").currentTime = 0; document.getElementById("notifSound").play().catch(()=>{}); } catch(e){}
        if (result.results) {
            const now = new Date();
            result.results.forEach(r => exportHistory.unshift({name:r.name,ok:r.ok,error:r.error||"",size:r.size||"",
                time:now.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}),date:now.toLocaleDateString()}));
        }
    });
}

/* ═══ EEL CALLBACKS ═══ */
eel.expose(start_timeline);
function start_timeline(name) {
    document.getElementById("progressBar").classList.add("show");
    document.getElementById("progFill").style.width = "0%";
    document.getElementById("progLabel").textContent = `Exporting: ${name}`;
    document.getElementById("progPct").textContent = "0%";
    document.getElementById("progEta").textContent = "ETA: calculating…";
}
eel.expose(update_progress);
function update_progress(pct, name, eta) {
    document.getElementById("progFill").style.width = pct + "%";
    document.getElementById("progPct").textContent = pct.toFixed(0) + "%";
    document.getElementById("progLabel").textContent = `Exporting: ${name}`;
    const h=String(Math.floor(eta/3600)).padStart(2,"0"), m=String(Math.floor((eta%3600)/60)).padStart(2,"0"), s=String(Math.floor(eta%60)).padStart(2,"0");
    document.getElementById("progEta").textContent = `ETA ${h}:${m}:${s}`;
}
eel.expose(timeline_error);
function timeline_error(name, msg) { showToast(`"${name}" failed: ${msg}`, true); }

/* ═══ HISTORY ═══ */
function renderHistory() {
    const el = document.getElementById("historyList");
    if (!exportHistory.length) { el.innerHTML = '<div class="empty-hint">No exports yet</div>'; return; }
    el.innerHTML = exportHistory.map(h => `
        <div class="hist-item">
            <div class="hist-icon ${h.ok?'ok':'fail'}">${h.ok?'✓':'✕'}</div>
            <div class="hist-info"><div class="hist-name">${esc(h.name)}</div><div class="hist-detail">${h.ok?h.size:esc(h.error)}</div></div>
            <div class="hist-time">${esc(h.time)}</div>
        </div>`).join("");
}

/* ═══ TOAST ═══ */
let toastTimer = null;
function showToast(msg, isError) {
    const el = document.getElementById("toast");
    el.textContent = msg; el.className = `toast show ${isError?'err':'ok'}`;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 4000);
}

/* ═══ HELPERS ═══ */
function esc(s) { const d = document.createElement("div"); d.textContent = s||""; return d.innerHTML; }
function formatDuration(sec) {
    if (!sec || sec <= 0) return "0:00";
    const m=Math.floor(sec/60),s=Math.floor(sec%60),h=Math.floor(m/60);
    return h > 0 ? `${h}:${String(m%60).padStart(2,"0")}:${String(s).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
}

/* ═══ INIT ═══ */
window.addEventListener("load", () => {
    initTheme(); initAccent(); initFullscreen(); initNav(); initSidebarResize(); initTooltip();
    addTimeline();
    eel.get_system_info()(info => {
        const badge = document.getElementById("encoderBadge");
        badge.textContent = info.encoder_name;
        if (!info.gpu_acceleration) badge.classList.add("cpu");
    });
});
