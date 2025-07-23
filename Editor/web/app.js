/* ---------- STATE ---------- */
let timelines = [];
let videos = [];
let timelineCounter = 0;
let outputPath = null;

/* ---------- THEME ---------- */
function applyTheme(mode){
    document.body.classList.toggle("dark", mode==="dark");
    document.getElementById("themeSwitch").checked = (mode==="dark");
    localStorage.setItem("theme", mode);
}
function initTheme(){
    const saved = localStorage.getItem("theme") || "light";
    applyTheme(saved);
    document.getElementById("themeSwitch").addEventListener("change", e=>{
        applyTheme(e.target.checked ? "dark" : "light");
    });
}

/* ---------- PICKERS ---------- */
function selectSource(){
    eel.choose_source()(result=>{
        if(!result){ showStatus("Source selection cancelled","error"); return; }
        videos = result.files;
        displayVideos();
        document.getElementById("srcLabel").textContent = result.path;
        showStatus(`Loaded ${videos.length} video(s)`,"success");
    });
}
function selectDestination(){
    eel.choose_destination()(dst=>{
        if(!dst){ showStatus("Destination not selected","error"); return; }
        outputPath = dst;
        document.getElementById("dstLabel").textContent = dst;
    });
}

/* ---------- VIDEO LIBRARY ---------- */
function displayVideos(){
    const list = document.getElementById("videoList");
    if(!videos.length){
        list.innerHTML='<div class="empty-state">No video files found</div>';
        return;
    }
    list.innerHTML = videos.map(v=>`
        <div class="video-item" draggable="true"
             data-video-name="${v.name}" data-video-path="${v.path}">
            <span class="video-icon">🎥</span>
            <div>
              <div style="font-weight:bold">${v.name}</div>
              <div style="font-size:12px" class="file-size">${v.size}</div>
            </div>
        </div>`).join('');
    list.querySelectorAll('.video-item').forEach(i=>i.addEventListener('dragstart',handleDragStart));
}

/* ---------- TIMELINE CRUD ---------- */
function addTimeline(){
    timelineCounter++;
    timelines.push({
        id:`tl_${timelineCounter}`,
        name:`Timeline ${timelineCounter}`,
        videos:[],
        fresh:true        // flag for first‑render animation
    });
    renderTimelines();
}
function removeTimeline(id){
    timelines = timelines.filter(t=>t.id!==id);
    renderTimelines();
}
function updateTimelineName(id,n){
    const t=timelines.find(t=>t.id===id);
    if(t) t.name=n;
}

/* ---------- RENDER TIMELINES (re‑order ready, no flash) ---------- */
function renderTimelines(){
    const c = document.getElementById("timelinesContainer");
    if(!timelines.length){
        c.innerHTML = '<div class="empty-state">Click “Add New Timeline” to create your first video timeline</div>';
        return;
    }

    c.innerHTML = timelines.map(t=>`
        <div class="timeline-container ${t.fresh ? 'fade-in':''}" data-id="${t.id}">
            <div class="timeline-header">
                <input type="text" class="timeline-name-input"
                       value="${t.name}" onchange="updateTimelineName('${t.id}',this.value)" />
                <button class="remove-timeline-btn" onclick="removeTimeline('${t.id}')">🗑️ Remove</button>
            </div>
            <div class="timeline" data-id="${t.id}"
                 ondrop="handleDrop(event)" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)">
                ${
                  !t.videos.length
                  ? '<div class="drag-placeholder">Drag videos here</div>'
                  : t.videos.map((v,i)=>`
                      <span class="timeline-video" draggable="true"
                            data-tl="${t.id}" data-idx="${i}"
                            ondragstart="handleTimelineVideoDragStart(event)"
                            ondragover="handleTimelineVideoDragOver(event)"
                            ondrop="handleTimelineVideoDrop(event)">
                          ${v.name}<span class="remove-video" onclick="removeVideoFromTimeline('${t.id}',${i})">✕</span>
                      </span>`).join('')
                }
            </div>
        </div>`).join('');

    // clear 'fresh' so animation won't replay
    timelines.forEach(t=>delete t.fresh);
}

/* ---------- DRAG & DROP ---------- */
function handleDragStart(e){
    e.dataTransfer.setData("text/plain",JSON.stringify({
        type:"lib",
        name:e.target.dataset.videoName,
        path:e.target.dataset.videoPath
    }));
}
function handleTimelineVideoDragStart(e){
    e.dataTransfer.setData("text/plain",JSON.stringify({
        type:"tl",
        tl:e.target.dataset.tl,
        idx:Number(e.target.dataset.idx)
    }));
}

/* Drop zones on timeline container */
function handleDragOver(e){ e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
function handleDragLeave(e){ e.currentTarget.classList.remove("drag-over"); }
function handleDrop(e){
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");
    const data = JSON.parse(e.dataTransfer.getData("text/plain"));
    const targetId = e.currentTarget.dataset.id;
    if(data.type==="lib") addVideoToTimeline(targetId,data);
    else moveVideo(data.tl,data.idx,targetId);
}

/* ----- RE‑ORDER: item‑over‑item ----- */
function handleTimelineVideoDragOver(e){ e.preventDefault(); }
function handleTimelineVideoDrop(e){
    e.preventDefault();
    const data = JSON.parse(e.dataTransfer.getData("text/plain"));
    const tgtTl  = e.target.dataset.tl;
    const tgtIdx = Number(e.target.dataset.idx);

    if(data.type==="lib"){
        addVideoToTimelineAt(tgtTl, data, tgtIdx);
    }else if(data.type==="tl"){
        insertExistingClip(data.tl, data.idx, tgtTl, tgtIdx);
    }
}

/* ----- helpers ----- */
function addVideoToTimeline(id,v){
    const tl = timelines.find(t=>t.id===id);
    if(!tl || tl.videos.some(x=>x.path===v.path)) return;
    tl.videos.push({name:v.name,path:v.path});
    renderTimelines();
}
function addVideoToTimelineAt(tlId, vid, atIdx){
    const tl = timelines.find(t=>t.id===tlId);
    if(!tl || tl.videos.some(v=>v.path===vid.path)) return;
    tl.videos.splice(atIdx, 0, {name:vid.name, path:vid.path});
    renderTimelines();
}
function moveVideo(src,idx,dst){
    const s = timelines.find(t=>t.id===src);
    const d = timelines.find(t=>t.id===dst);
    if(!s||!d) return;
    const clip = s.videos.splice(idx,1)[0];
    d.videos.push(clip);
    renderTimelines();
}
function insertExistingClip(srcTl, srcIdx, dstTl, dstIdx){
    const s = timelines.find(t=>t.id===srcTl);
    const d = timelines.find(t=>t.id===dstTl);
    if(!s||!d) return;
    const clip = s.videos.splice(srcIdx,1)[0];
    if(srcTl === dstTl && srcIdx < dstIdx) dstIdx--;
    d.videos.splice(dstIdx,0,clip);
    renderTimelines();
}
function removeVideoFromTimeline(id,i){
    const t=timelines.find(t=>t.id===id);
    if(t){ t.videos.splice(i,1); renderTimelines(); }
}

/* ---------- EXPORT ---------- */
function exportTimelines(){
    if(!outputPath){ showStatus("Pick a destination first","error"); return; }
    const used = timelines.filter(t=>t.videos.length);
    if(!used.length){ showStatus("No videos in timelines","error"); return; }

    document.getElementById("exportBtn").disabled = true;
    document.getElementById("progressBar").style.display = "block";

    eel.export_timelines(JSON.stringify(used), outputPath)((msg)=>{
        showStatus("✅ "+msg,"success");
        document.getElementById("exportBtn").disabled = false;
        document.getElementById("progressFill").style.width = "0%";
        document.getElementById("progressBar").style.display = "none";
        document.getElementById("progressText").textContent = "";
        document.getElementById("etaText").textContent = "";
    });
}

/* ---------- TIMELINE START RESET ---------- */
eel.expose(start_timeline);
function start_timeline(name){
    document.getElementById("progressFill").style.width = "0%";
    document.getElementById("progressBar").style.display = "block";
    document.getElementById("progressText").textContent = `Processing: ${name} • 0 %`;
    document.getElementById("etaText").textContent = "ETA: calculating…";
}

/* ---------- LIVE PROGRESS ---------- */
eel.expose(update_progress);
function update_progress(percent, tlName, etaSec){
    document.getElementById("progressFill").style.width = percent + "%";

    const h = String(Math.floor(etaSec/3600)).padStart(2,"0");
    const m = String(Math.floor((etaSec%3600)/60)).padStart(2,"0");
    const s = String(Math.floor(etaSec%60)).padStart(2,"0");

    document.getElementById("progressText").textContent =
        `Processing: ${tlName}  •  ${percent.toFixed(1)} %`;
    document.getElementById("etaText").textContent =
        `ETA: ${h}:${m}:${s}`;
}

/* ---------- STATUS ---------- */
function showStatus(msg,type){
    const el=document.getElementById("statusMessage");
    el.textContent=msg;
    el.className=`status-message status-${type}`;
    el.style.display="block";
    if(type==="success") setTimeout(()=>el.style.display="none",5000);
}

/* ---------- INIT ---------- */
window.addEventListener("load", ()=>{
    initTheme();
    addTimeline();
});
