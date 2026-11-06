(() => {
  const canvas = document.getElementById("orb");
  const ctx = canvas.getContext("2d");
  const stateChip = document.getElementById("stateChip");
  const orbLabel = document.getElementById("orbLabel");
  let state = "idle";
  let t = 0;

  function draw() {
    t += 0.016;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    ctx.clearRect(0, 0, w, h);

    const pulse =
      state === "speaking" ? 1.08 + Math.sin(t * 8) * 0.06 :
      state === "listening" ? 1.05 + Math.sin(t * 4) * 0.04 :
      state === "thinking" ? 1.03 + Math.sin(t * 2.2) * 0.03 :
      state === "executing" ? 1.06 + Math.sin(t * 6) * 0.05 :
      1 + Math.sin(t * 1.2) * 0.015;

    const r = 110 * pulse;
    const g = ctx.createRadialGradient(cx, cy, 10, cx, cy, r * 1.6);
    g.addColorStop(0, "rgba(180, 255, 255, 0.95)");
    g.addColorStop(0.35, "rgba(62, 207, 207, 0.55)");
    g.addColorStop(1, "rgba(7, 11, 18, 0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 1.55, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(62, 207, 207, 0.85)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // waveform ring
    ctx.beginPath();
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      const amp =
        state === "speaking" || state === "listening"
          ? 12 + Math.sin(t * 10 + i * 0.4) * 10
          : 4 + Math.sin(t * 2 + i * 0.2) * 2;
      const rr = r + 18 + amp;
      const x = cx + Math.cos(a) * rr;
      const y = cy + Math.sin(a) * rr;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = "rgba(62, 207, 207, 0.35)";
    ctx.stroke();

    requestAnimationFrame(draw);
  }
  draw();

  function setState(s) {
    state = s || "idle";
    stateChip.textContent = state;
    orbLabel.textContent = state;
  }

  async function refresh() {
    try {
      const st = await (await fetch("/api/status")).json();
      document.getElementById("provider").value = st.provider || "openai";
      document.getElementById("model").value = st.model || "";
      document.getElementById("micInd").classList.toggle("on", st.mic_mode === "open");
      document.getElementById("camInd").classList.toggle("on", !!st.webcam_enabled);
      document.getElementById("actInd").classList.toggle("on", (st.pending || []).length > 0);
      if (st.stopped) setState("idle");
      else if ((st.pending || []).length) setState("executing");
      document.getElementById("usage").textContent = JSON.stringify(st.usage, null, 2);

      const pending = document.getElementById("pending");
      pending.innerHTML = "";
      (st.pending || []).forEach((p) => {
        const div = document.createElement("div");
        div.className = "item";
        div.innerHTML = `<div><strong>${p.tool}</strong> (${p.risk})</div><div>${p.preview}</div>`;
        const yes = document.createElement("button");
        yes.textContent = "Approve";
        yes.onclick = () => approve(p.id, true);
        const no = document.createElement("button");
        no.textContent = "Deny";
        no.onclick = () => approve(p.id, false);
        div.appendChild(yes);
        div.appendChild(no);
        pending.appendChild(div);
      });
      if (!(st.pending || []).length) {
        pending.innerHTML = "<div class='item'>No pending actions</div>";
      }
    } catch (_) { /* dashboard may start before API is ready */ }

    try {
      const audit = await (await fetch("/api/audit")).json();
      const box = document.getElementById("audit");
      box.innerHTML = (audit.events || []).slice().reverse().slice(0, 12).map((e) =>
        `<div class="item">${e.event}${e.tool ? " · " + e.tool : ""}</div>`
      ).join("") || "<div class='item'>No activity yet</div>";
    } catch (_) {}

    try {
      const mem = await (await fetch("/api/memory")).json();
      const box = document.getElementById("memory");
      box.innerHTML = (mem.items || []).slice(0, 8).map((m) =>
        `<div class="item"><strong>${m.title}</strong><div>${(m.snippet || "").slice(0, 120)}</div></div>`
      ).join("") || "<div class='item'>Memory empty</div>";
    } catch (_) {}
  }

  async function approve(id, approved) {
    await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, approved }),
    });
    refresh();
  }

  document.getElementById("stopBtn").onclick = async () => {
    await fetch("/api/stop", { method: "POST", body: "{}" });
    setState("idle");
    refresh();
  };

  document.getElementById("applyModel").onclick = async () => {
    await fetch("/api/provider", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: document.getElementById("provider").value,
        model: document.getElementById("model").value,
      }),
    });
    refresh();
  };

  refresh();
  setInterval(refresh, 2000);
})();
