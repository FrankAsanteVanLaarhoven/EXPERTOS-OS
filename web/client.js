'use strict';

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const state = {
  activeTab: 'world',
  agents: [],
  selected: 'master',
  events: [],
  currentFeed: 'seismic',
  filter: 'all',
  modelConfigured: false,
  paused: false,
  angle: -8,
  tilt: 12,
  zoom: 1,
  drag: false,
  running: false,
  activeGraph: null,
  pendingApprovals: [],
  packages: [],
  selectedPackage: null
};

const cap = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));

const fmtUTC = d => {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleString('en-GB', {
      timeZone: 'UTC', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    }) + ' UTC';
  } catch {
    return String(d);
  }
};

function toast(msg) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => el.classList.remove('show'), 3800);
}

async function api(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  });
  const data = await r.json().catch(() => ({ detail: 'Unparseable server response' }));
  if (!r.ok) {
    const err = typeof data.detail === 'string' ? data.detail : (data.detail?.message || data.error || JSON.stringify(data.detail || data));
    throw new Error(err);
  }
  return data;
}

// Tab Switching
function switchTab(tabId) {
  state.activeTab = tabId;
  $$('.nav-tab').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabId);
  });
  $$('.tab-pane').forEach(p => {
    p.classList.toggle('hidden', p.id !== 'pane-' + tabId);
  });
  const names = {
    world: 'WORLD OVERVIEW',
    orchestration: 'MULTI-AGENT DAG',
    approvals: 'MCP CAPABILITY BROKER',
    evidence: 'STRATUM-X EVIDENCE AUDIT'
  };
  $('#current-area').textContent = names[tabId] || 'OPERATIONS';
  if (tabId === 'approvals') loadApprovals();
  if (tabId === 'evidence') loadEvidence();
}

// Agent Listing & Selection
function renderAgents() {
  const list = $('#agent-list');
  list.replaceChildren();
  for (const a of state.agents) {
    const b = document.createElement('button');
    b.className = 'agent-entry' + (a.id === state.selected ? ' active' : '');
    b.style.setProperty('--agent-color', a.color || '#a6aaff');
    b.title = a.expertise;
    b.innerHTML = `
      <span class="agent-avatar">${cap(a.icon || '✧')}</span>
      <span class="agent-text">
        <strong>${cap(a.name)}</strong>
        <small>${cap(a.expertise)}</small>
      </span>`;
    b.onclick = () => selectAgent(a.id);
    list.appendChild(b);
  }
  $('#agent-count').textContent = String(state.agents.length).padStart(2, '0');
}

function selectAgent(id) {
  state.selected = id;
  const a = state.agents.find(x => x.id === id);
  if (!a) return;
  renderAgents();
  $('#chat-agent-title').textContent = a.name;
  $('#lens-title').textContent = a.name;
  $('#lens-subtitle').textContent = a.expertise.length > 55 ? a.expertise.slice(0, 52) + '…' : a.expertise;
  $('#conversation').innerHTML = `
    <div class="empty-convo">
      <span>${cap(a.icon)}</span>
      <strong>${cap(a.name)} ready.</strong>
      <p>${cap(a.expertise)}. Requests are routed through the configured provider; answers are strictly labelled MODEL_UNVERIFIED until independently assessed.</p>
    </div>`;
  $('#run-state').textContent = 'READY';
  loadEphemeral(id);
}

// Ephemeral Safe UI Blueprint
let viewEpoch = 0;
async function loadEphemeral(id) {
  const epoch = ++viewEpoch;
  $('#ephemeral-grid').innerHTML = '<div class="ephemeral-loading">Generating typed task context…</div>';
  try {
    const v = await api('/api/agents/' + encodeURIComponent(id) + '/view');
    if (epoch !== viewEpoch) return;
    const allowed = new Set(['globe', 'timeline', 'evidence_table', 'agent_feed', 'forecast_calibration', 'source_graph', 'code_diff', 'task_plan']);
    $('#ephemeral-title').textContent = v.title;
    const grid = $('#ephemeral-grid');
    grid.replaceChildren();
    for (const b of v.blocks) {
      if (!allowed.has(b.type)) continue;
      const el = document.createElement('div');
      el.className = 'ephemeral-card';
      const top = document.createElement('div');
      top.className = 'ephemeral-card-top';
      const typ = document.createElement('span');
      typ.textContent = b.type.replaceAll('_', ' ').toUpperCase();
      const badge = document.createElement('span');
      badge.textContent = b.state || 'UNCONNECTED';
      top.append(typ, badge);
      const h = document.createElement('strong');
      h.textContent = b.title;
      const p = document.createElement('p');
      p.textContent = b.description;
      el.append(top, h, p);
      grid.append(el);
    }
    $('#ephemeral-ttl').textContent = Math.floor(v.ttl_seconds / 60) + ' MIN SESSION';
    setTimeout(() => {
      if (epoch === viewEpoch) {
        grid.innerHTML = '<div class="ephemeral-disposed">This ephemeral view expired after its TTL. Regenerate to resume.</div>';
      }
    }, Math.min(v.ttl_seconds * 1000, 2147483647));
  } catch (err) {
    if (epoch === viewEpoch) $('#ephemeral-grid').textContent = 'Workbench unavailable: ' + err.message;
  }
}

function modal(open) {
  $('#builder-modal').classList.toggle('hidden', !open);
  if (open) setTimeout(() => $('#agent-form [name=name]').focus(), 40);
}

async function refreshAgents() {
  const data = await api('/api/agents');
  state.agents = data.agents;
  renderAgents();
}

function addMsg(who, title, content) {
  const area = $('#conversation');
  area.querySelector('.empty-convo')?.remove();
  const el = document.createElement('div');
  el.className = 'chat-msg ' + who;
  const h = document.createElement('small');
  h.textContent = title;
  const c = document.createElement('div');
  c.textContent = content;
  el.append(h, c);
  area.append(el);
  area.scrollTop = area.scrollHeight;
  return el;
}

async function runAgent(e) {
  e.preventDefault();
  if (state.running) return;
  const prompt = $('#chat-input').value.trim();
  if (!prompt) return;
  const agent = state.agents.find(a => a.id === state.selected);
  state.running = true;
  $('#chat-form button[type=submit]').disabled = true;
  $('#run-state').textContent = 'INFERENCE';
  addMsg('user', 'YOUR REQUEST', prompt);
  $('#chat-input').value = '';
  const pending = addMsg('assistant', 'AGENT · RUNNING', 'Routing to model provider…');
  try {
    const result = await api('/api/agent/run', {
      method: 'POST',
      body: JSON.stringify({ agent_id: state.selected, prompt, model: $('#model-select').value })
    });
    pending.querySelector('small').textContent = (agent ? agent.name : state.selected) + ' · ' + result.model + ' · UNVERIFIED';
    pending.lastElementChild.textContent = result.answer;
    $('#run-state').textContent = 'COMPLETED';
    toast('Run saved: ' + result.run_id + ' (response unverified)');
  } catch (err) {
    pending.querySelector('small').textContent = 'RUN NOT COMPLETED';
    pending.lastElementChild.textContent = err.message;
    $('#run-state').textContent = 'FAILED';
    toast(err.message);
  } finally {
    state.running = false;
    $('#chat-form button[type=submit]').disabled = false;
    $('#conversation').scrollTop = $('#conversation').scrollHeight;
  }
}

async function loadStatus() {
  try {
    const s = await api('/api/status');
    state.modelConfigured = s.openrouter_configured;
    $('#metric-router').innerHTML = s.openrouter_configured ? 'ON <small>provider</small>' : 'OFF <small>provider</small>';
    $('#router-note').textContent = s.openrouter_configured ? 'OpenRouter server key configured' : 'Configure server-only key';
    $('#system-state').textContent = s.openrouter_configured ? 'MODEL ROUTER READY' : 'LOCAL PROTOTYPE';
    if (s.openrouter_configured) {
      const m = await api('/api/models');
      const sel = $('#model-select');
      for (const model of m.models) {
        const opt = document.createElement('option');
        opt.value = model.id;
        opt.textContent = model.name;
        sel.append(opt);
      }
    }
  } catch (e) {
    toast('Status lookup: ' + e.message);
  }
}

// Multi-Feed World Intelligence
async function refreshWorld(feed = state.currentFeed) {
  state.currentFeed = feed;
  try {
    const data = await api('/api/world/events?feed=' + encodeURIComponent(feed));
    state.events = data.events || [];
    $('#metric-events').innerHTML = state.events.length + ' <small>events</small>';
    $('#events-note').textContent = 'Feed ' + fmtUTC(data.feed_generated_at || data.retrieved_at);
    $('#feed-source').textContent = (data.source || 'WORLD INTELLIGENCE') + ' / ' + (data.mode || 'VERIFIED');
    $('#feed-timestamp').textContent = '• Generated ' + fmtUTC(data.feed_generated_at);
    $('#live-status').textContent = 'LIVE / VERIFIED';
    $('#live-status').parentElement.style.borderColor = '#306a57';
    $('#live-status').parentElement.style.background = '#152d29';
    $('#source-indicator').textContent = 'CONNECTED';
    $('#source-indicator').classList.remove('offline');
    $('#stream-mode').textContent = data.mode === 'LIVE_SOURCE' ? 'OBSERVED' : 'NEAR REAL-TIME';
    $('#stream-mode').classList.add('live');
    renderFeed();
  } catch (e) {
    state.events = [];
    $('#feed-source').textContent = 'SOURCE OFFLINE';
    $('#live-status').textContent = 'SOURCE OFFLINE';
    $('#metric-events').innerHTML = '— <small>offline</small>';
    $('#events-note').textContent = 'No synthetic observations substituted';
    $('#stream-mode').textContent = 'OFFLINE';
    renderFeed();
    toast('Observation feed offline: ' + e.message);
  }
}

function renderFeed() {
  const el = $('#event-feed');
  el.replaceChildren();
  let filtered = [...state.events];
  if (state.filter === 'major') {
    filtered = filtered.filter(e => (e.magnitude && e.magnitude >= 5.5) || e.value > 1000 || e.status_level === 'RESTRICTED_CONVOY');
  }
  if (state.filter === 'recent') {
    filtered = filtered.slice(0, 8);
  } else {
    filtered = filtered.slice(0, 16);
  }
  $('#signal-count').textContent = filtered.length;
  if (!filtered.length) {
    el.innerHTML = '<div class="feed-placeholder">No observations available for the active filter. The system never fabricates synthetic events.</div>';
    return;
  }
  for (const e of filtered) {
    const node = document.createElement('div');
    node.className = 'event-entry';
    const tagText = e.magnitude ? `M ${Number(e.magnitude).toFixed(1)}` : (e.indicator || e.status_level || 'OBS');
    const isMajor = (e.magnitude && e.magnitude >= 5.5) || e.status_level === 'RESTRICTED_CONVOY';
    node.innerHTML = `
      <div class="event-top">
        <span class="event-tag ${isMajor ? '' : 'moderate'}">${cap(tagText)}</span>
        <span class="event-time">${cap(fmtUTC(e.occurred_at))}</span>
      </div>
      <h4>${cap(e.title)}</h4>
      <p>${e.latitude != null ? Number(e.latitude).toFixed(2) + '° lat · ' + Number(e.longitude).toFixed(2) + '° lon' : ''} ${e.value != null ? '· ' + e.value + ' ' + (e.unit || '') : ''}</p>
      <span class="event-source">${cap(e.source_attribution || 'VERIFIED SOURCE')} ↗</span>
    `;
    node.addEventListener('click', () => {
      if (e.longitude != null && e.latitude != null) {
        state.angle = -e.longitude;
        state.tilt = e.latitude * 0.26;
        $('#coordinates').textContent = `${Math.abs(e.latitude).toFixed(2)}° ${e.latitude >= 0 ? 'N' : 'S'} · ${Math.abs(e.longitude).toFixed(2)}° ${e.longitude >= 0 ? 'E' : 'W'}`;
        toast('Planet centered on ' + (e.title || e.id));
      }
    });
    el.append(node);
  }
}

// Multi-Agent Orchestration Workflow
async function decomposeMission(objective) {
  try {
    $('#decompose-submit').disabled = true;
    toast('Decomposing mission across specialist agents…');
    const data = await api('/api/orchestration/decompose', {
      method: 'POST',
      body: JSON.stringify({ objective })
    });
    state.activeGraph = data.graph;
    renderGraph(data.graph);
    $('#step-dag-btn').disabled = false;
    toast('Task graph initialized: ' + data.graph.graph_id);
  } catch (err) {
    toast('Decomposition error: ' + err.message);
  } finally {
    $('#decompose-submit').disabled = false;
  }
}

async function stepGraph() {
  if (!state.activeGraph) return;
  const btn = $('#step-dag-btn');
  btn.disabled = true;
  try {
    toast('Executing available ready nodes in DAG…');
    const data = await api(`/api/orchestration/graphs/${state.activeGraph.graph_id}/step`, { method: 'POST' });
    state.activeGraph = data.graph;
    renderGraph(data.graph);
    toast('DAG advanced: status ' + data.graph.status);
  } catch (err) {
    toast('Step failure: ' + err.message);
  } finally {
    btn.disabled = state.activeGraph.status === 'completed';
  }
}

function renderGraph(graph) {
  $('#dag-status').textContent = graph.status.toUpperCase();
  const container = $('#dag-container');
  container.replaceChildren();
  for (const [nid, node] of Object.entries(graph.nodes)) {
    const card = document.createElement('div');
    card.className = `dag-node-card ${node.status}`;
    card.innerHTML = `
      <div class="dag-node-top">
        <span class="dag-node-role">${cap(node.assigned_agent_id.toUpperCase())}</span>
        <span class="dag-node-status">${cap(node.status.toUpperCase())}</span>
      </div>
      <h4>${cap(node.title)}</h4>
      <p>${cap(node.prompt)}</p>
      ${node.result ? `<div class="dag-node-result">${cap(node.result)}</div>` : ''}
    `;
    container.append(card);
  }

  // Render Checkpoints
  const cpList = $('#checkpoint-list');
  cpList.replaceChildren();
  if (!graph.checkpoints || !graph.checkpoints.length) {
    cpList.innerHTML = '<div class="empty-list">No checkpoints recorded yet.</div>';
    return;
  }
  for (const cp of [...graph.checkpoints].reverse()) {
    const item = document.createElement('div');
    item.className = 'cp-item';
    item.innerHTML = `
      <div class="cp-item-top">
        <span class="cp-id">${cap(cp.checkpoint_id)}</span>
        <button class="dag-btn">Restore ↺</button>
      </div>
      <div>Time: ${cap(fmtUTC(cp.timestamp))}</div>
      <div>Status: ${cap(cp.status)}</div>
    `;
    item.querySelector('button').onclick = async () => {
      try {
        const res = await api(`/api/orchestration/graphs/${graph.graph_id}/recover?checkpoint_id=${cp.checkpoint_id}`, { method: 'POST' });
        state.activeGraph = res.graph;
        renderGraph(res.graph);
        toast('Recovered to checkpoint ' + cp.checkpoint_id);
      } catch (err) {
        toast('Recovery failed: ' + err.message);
      }
    };
    cpList.append(item);
  }
}

// MCP Approvals & Tool Registry
async function loadApprovals() {
  try {
    const [apprData, toolsData] = await Promise.all([
      api('/api/mcp/approvals'),
      api('/api/mcp/tools')
    ]);
    state.pendingApprovals = apprData.pending_approvals || [];
    $('#approval-badge').textContent = String(state.pendingApprovals.length);
    
    // Render Approvals
    const list = $('#approvals-list');
    list.replaceChildren();
    if (!state.pendingApprovals.length) {
      list.innerHTML = '<div class="empty-list">No pending side-effect approval requests. All execution channels secure.</div>';
    } else {
      for (const a of state.pendingApprovals) {
        const card = document.createElement('div');
        card.className = 'approval-card';
        card.innerHTML = `
          <div class="approval-card-top">
            <strong>${cap(a.tool_name)}</strong>
            <span class="approval-tag">${cap(a.risk_level.toUpperCase())}</span>
          </div>
          <div>Agent: <b>${cap(a.agent_id)}</b></div>
          <div style="margin:4px 0; color:#859bb0;">Params: <code>${cap(JSON.stringify(a.parameters))}</code></div>
          <div class="approval-actions">
            <button class="approve-btn">Approve & Execute ↗</button>
            <button class="reject-btn">Reject ×</button>
          </div>
        `;
        card.querySelector('.approve-btn').onclick = () => decideApproval(a.request_id, 'approved');
        card.querySelector('.reject-btn').onclick = () => decideApproval(a.request_id, 'rejected');
        list.append(card);
      }
    }

    // Render Tools
    const toolList = $('#tools-list');
    toolList.replaceChildren();
    for (const t of toolsData.tools || []) {
      const item = document.createElement('div');
      item.className = 'tool-item';
      item.innerHTML = `
        <div class="tool-top">
          <span class="tool-name">${cap(t.name)}</span>
          <span class="dag-status-pill">${cap(t.risk_level)}</span>
        </div>
        <p style="margin:4px 0; color:#869baa;">${cap(t.description)}</p>
      `;
      toolList.append(item);
    }
  } catch (err) {
    toast('MCP load error: ' + err.message);
  }
}

async function decideApproval(reqId, decision) {
  try {
    await api(`/api/mcp/approvals/${reqId}/decide`, {
      method: 'POST',
      body: JSON.stringify({ decision, operator: 'workspace-admin' })
    });
    toast(`Request ${reqId} ${decision}`);
    loadApprovals();
  } catch (err) {
    toast('Decision error: ' + err.message);
  }
}

// STRATUM-X Evidence Audit
async function loadEvidence() {
  try {
    const data = await api('/api/evidence/packages?limit=25');
    state.packages = data.packages || [];
    const list = $('#packages-list');
    list.replaceChildren();
    if (!state.packages.length) {
      list.innerHTML = '<div class="empty-list">No evidence packages recorded yet.</div>';
      return;
    }
    for (const pkg of state.packages) {
      const item = document.createElement('div');
      item.className = 'pkg-item';
      item.style.cursor = 'pointer';
      item.innerHTML = `
        <div class="pkg-top">
          <span class="pkg-id">${cap(pkg.id)}</span>
          <span class="dag-status-pill">${cap(pkg.classification)}</span>
        </div>
        <div style="color:#788f9f;">Source: ${cap(pkg.source_id)}</div>
        <div style="color:#607380; font-size:9.5px;">Observed: ${cap(fmtUTC(pkg.observed_at))}</div>
      `;
      item.onclick = () => inspectPackage(pkg.id);
      list.append(item);
    }
  } catch (err) {
    toast('Evidence load error: ' + err.message);
  }
}

async function inspectPackage(pkgId) {
  try {
    const data = await api(`/api/evidence/packages/${pkgId}`);
    const pkg = data.package;
    state.selectedPackage = pkg;
    $('#inspector-badge').textContent = pkg.classification;
    const insp = $('#inspector-content');
    insp.innerHTML = `
      <div class="verified-stamp">STRATUM-X SEALED ENVELOPE</div>
      <h4 style="margin:4px 0 8px; font-family:'Space Grotesk'; font-size:13px;">${cap(pkg.id)}</h4>
      <div><strong>Source Root:</strong> ${cap(pkg.source_id)} (<code>${cap(pkg.source_url)}</code>)</div>
      <div><strong>Classification:</strong> ${cap(pkg.classification)}</div>
      <div style="margin:8px 0; padding:8px; background:#080e16; border-radius:5px;">
        <strong>Bitemporal Timeline:</strong>
        <div>• Observed At: ${cap(fmtUTC(pkg.temporal.observed_at))}</div>
        <div>• Available At: ${cap(fmtUTC(pkg.temporal.available_at))}</div>
        <div>• Ingested At: ${cap(fmtUTC(pkg.temporal.ingested_at))}</div>
      </div>
      <div><strong>Content Hash (SHA-256):</strong> <code>${cap(pkg.content_hash)}</code></div>
      <div><strong>DSSE HMAC Signature:</strong> <code>${cap(pkg.signature.slice(0, 32))}…</code></div>
      <div style="margin-top:12px;">
        <button id="verify-now-btn" class="dag-btn" style="background:#1d463b; color:#8df5d4;">Verify Signature &amp; Causality ↗</button>
      </div>
    `;
    $('#verify-now-btn').onclick = async () => {
      try {
        const v = await api('/api/evidence/verify', { method: 'POST', body: JSON.stringify(pkg) });
        if (v.valid) {
          toast('Package cryptographically valid: Signature & Causality verified');
        } else {
          toast('Verification failed: ' + v.issues.join('; '));
        }
      } catch (err) {
        toast('Verification error: ' + err.message);
      }
    };
  } catch (err) {
    toast('Inspect error: ' + err.message);
  }
}

async function runAdversarialBenchmark() {
  try {
    toast('Running geospatial adversarial evaluation protocol…');
    const bm = await api('/api/spatialforge/benchmark', { method: 'POST' });
    toast(`Benchmark Passed: ${bm.passed_cases}/${bm.total_cases} cases. Abstention precision: ${(bm.adversarial_precision * 100).toFixed(0)}%`);
  } catch (err) {
    toast('Benchmark error: ' + err.message);
  }
}

// Orthographic Globe Rendering
const canvas = $('#globe');
const ctx = canvas.getContext('2d');
let W = 0, H = 0, dpr = 1, frame = 0;
const deg = Math.PI / 180;
const land = [
  [[-168, 72], [-140, 71], [-130, 60], [-125, 49], [-117, 33], [-105, 25], [-97, 18], [-85, 22], [-82, 29], [-66, 45], [-55, 51], [-63, 61], [-83, 62], [-93, 73], [-125, 72]],
  [[-81, 12], [-69, 9], [-61, 0], [-53, -13], [-45, -24], [-52, -35], [-66, -55], [-74, -44], [-75, -22], [-81, -5]],
  [[-12, 36], [2, 45], [15, 48], [25, 53], [39, 58], [30, 70], [8, 71], [-8, 59], [-12, 36]],
  [[-17, 37], [10, 37], [34, 28], [48, 12], [43, -12], [33, -28], [19, -35], [12, -34], [8, -19], [-2, -6], [-17, 17]],
  [[26, 40], [44, 50], [70, 55], [90, 70], [130, 68], [172, 61], [166, 42], [146, 35], [129, 31], [117, 24], [107, 10], [98, 5], [85, 14], [70, 25], [54, 24], [45, 35]],
  [[112, -11], [137, -11], [154, -27], [146, -39], [129, -35], [115, -24]],
  [[-52, 60], [-36, 70], [-42, 83], [-57, 83]],
  [[46, -13], [50, -19], [48, -25], [44, -26]],
  [[130, 32], [136, 34], [141, 45], [145, 42], [141, 34]],
  [[-9, 58], [1, 58], [2, 51], [-5, 50]],
  [[-180, -74], [-95, -76], [-40, -81], [55, -77], [130, -75], [180, -78]]
];

function resize() {
  const r = canvas.getBoundingClientRect();
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  W = r.width;
  H = r.height;
  canvas.width = Math.floor(W * dpr);
  canvas.height = Math.floor(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function project(lon, lat) {
  const a = (lon + state.angle) * deg;
  const b = lat * deg;
  const tilt = state.tilt * deg;
  const x = Math.cos(b) * Math.sin(a);
  const z = Math.cos(b) * Math.cos(a);
  const y = Math.sin(b);
  const y2 = y * Math.cos(tilt) - z * Math.sin(tilt);
  const z2 = y * Math.sin(tilt) + z * Math.cos(tilt);
  return { x, y: y2, z: z2 };
}

function poly(points, r, cx, cy, fill, stroke) {
  let segments = [], path = [];
  for (let i = 0; i < points.length; i++) {
    const p = project(points[i][0], points[i][1]);
    if (p.z > 0.015) {
      path.push([cx + p.x * r, cy - p.y * r]);
    } else {
      if (path.length > 2) segments.push(path);
      path = [];
    }
  }
  if (path.length > 2) segments.push(path);
  for (const seg of segments) {
    ctx.beginPath();
    seg.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
  }
}

function lineSphere(points, r, cx, cy, color, width = 1) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  let drawing = false;
  ctx.beginPath();
  for (const [lon, lat] of points) {
    const p = project(lon, lat);
    if (p.z > 0) {
      if (!drawing) { ctx.moveTo(cx + p.x * r, cy - p.y * r); drawing = true; }
      else { ctx.lineTo(cx + p.x * r, cy - p.y * r); }
    } else {
      if (drawing) ctx.stroke();
      ctx.beginPath();
      drawing = false;
    }
  }
  if (drawing) ctx.stroke();
}

function renderGlobe() {
  if (!W || !H) resize();
  ctx.clearRect(0, 0, W, H);
  const cx = W * 0.55, cy = H * 0.47;
  const r = Math.min(W * 0.43, H * 0.51) * state.zoom;
  
  // Outer atmosphere glow
  const atmosphere = ctx.createRadialGradient(cx, cy, r * 0.65, cx, cy, r * 1.33);
  atmosphere.addColorStop(0, '#0c405022');
  atmosphere.addColorStop(0.76, '#1c9dad0d');
  atmosphere.addColorStop(1, '#3bd7c500');
  ctx.fillStyle = atmosphere;
  ctx.beginPath();
  ctx.arc(cx, cy, r * 1.33, 0, Math.PI * 2);
  ctx.fill();

  // Dark shaded sphere
  const sphere = ctx.createRadialGradient(cx - r * 0.36, cy - r * 0.32, r * 0.07, cx + r * 0.12, cy + r * 0.06, r * 1.3);
  sphere.addColorStop(0, '#17394a');
  sphere.addColorStop(0.5, '#0d2938');
  sphere.addColorStop(0.85, '#081723');
  sphere.addColorStop(1, '#06101c');
  ctx.fillStyle = sphere;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.clip();

  // Graticule
  for (let lat = -75; lat <= 75; lat += 15) {
    const pts = [];
    for (let lon = -180; lon <= 180; lon += 3) pts.push([lon, lat]);
    lineSphere(pts, r, cx, cy, '#2f7a8b2b', 0.65);
  }
  for (let lon = -180; lon < 180; lon += 15) {
    const pts = [];
    for (let lat = -90; lat <= 90; lat += 3) pts.push([lon, lat]);
    lineSphere(pts, r, cx, cy, '#2f7a8b29', 0.65);
  }

  // Land masses
  for (const cont of land) poly(cont, r, cx, cy, '#22607842', '#52c4c451');
  for (const cont of land) poly(cont.map(([lo, la]) => [lo, la + 0.6]), r, cx, cy, null, '#65d9c022');

  // Observation Markers
  for (const e of state.events) {
    if (e.longitude == null || e.latitude == null) continue;
    const p = project(e.longitude, e.latitude);
    if (p.z <= 0) continue;
    const x = cx + p.x * r, y = cy - p.y * r;
    const mag = Math.max(1, Math.min(6, (e.magnitude || 4) - 3));
    
    if (state.currentFeed === 'seismic') {
      ctx.strokeStyle = 'rgba(78,233,200,.35)';
      ctx.beginPath();
      ctx.arc(x, y, mag * 2.2 + ((frame / 4) % 13), 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = (e.magnitude && e.magnitude >= 5.5) ? '#ffb679' : '#52eaca';
      ctx.beginPath();
      ctx.arc(x, y, Math.max(1.5, mag * 1.2), 0, Math.PI * 2);
      ctx.fill();
    } else if (state.currentFeed === 'economic') {
      ctx.fillStyle = '#629cec';
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.fillStyle = '#e9a670';
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.restore();

  // Rim ring
  ctx.strokeStyle = '#4bd4c454';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();

  if (!state.paused && !state.drag) state.angle = (state.angle + 0.045) % 360;
  frame++;
  requestAnimationFrame(renderGlobe);
}

// Pointer Events for 3D Globe
const start = {};
canvas.addEventListener('pointerdown', e => {
  state.drag = true;
  start.x = e.clientX;
  start.y = e.clientY;
  start.angle = state.angle;
  start.tilt = state.tilt;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', e => {
  if (!state.drag) return;
  state.angle = start.angle + (e.clientX - start.x) * 0.42;
  state.tilt = Math.max(-55, Math.min(55, start.tilt + (e.clientY - start.y) * 0.25));
});
canvas.addEventListener('pointerup', () => (state.drag = false));
canvas.addEventListener('pointercancel', () => (state.drag = false));
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  state.zoom = Math.max(0.65, Math.min(1.38, state.zoom + (e.deltaY < 0 ? 0.06 : -0.06)));
}, { passive: false });

function attachEvents() {
  // Navigation tabs
  $$('.nav-tab').forEach(b => {
    b.onclick = () => switchTab(b.dataset.tab);
  });

  // Ephemeral controls
  $('#ephemeral-refresh').onclick = () => loadEphemeral(state.selected);
  $('#ephemeral-dispose').onclick = () => {
    viewEpoch++;
    $('#ephemeral-grid').innerHTML = '<div class="ephemeral-disposed">Transient workbench disposed. Results preserved in run ledger.</div>';
    $('#ephemeral-title').textContent = 'Workbench disposed';
  };

  // Agent Foundry Modal
  ['#new-agent', '#open-builder'].forEach(s => ($(s).onclick = () => modal(true)));
  ['#close-builder', '#cancel-builder'].forEach(s => ($(s).onclick = () => modal(false)));
  $('#builder-modal').onclick = e => { if (e.target.id === 'builder-modal') modal(false); };
  
  $('#agent-form').onsubmit = async e => {
    e.preventDefault();
    const b = new FormData(e.currentTarget);
    const payload = Object.fromEntries(b.entries());
    try {
      const r = await api('/api/agents', { method: 'POST', body: JSON.stringify(payload) });
      await refreshAgents();
      selectAgent(r.agent.id);
      modal(false);
      $('#agent-form').reset();
      toast('Agent manifest created: ' + r.agent.name);
    } catch (err) {
      toast('Agent creation failed: ' + err.message);
    }
  };

  // Run chat form
  $('#chat-form').onsubmit = runAgent;
  $('#chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      $('#chat-form').requestSubmit();
    }
  });

  // Global keyboard shortcuts
  document.addEventListener('keydown', e => {
    if (e.key.toLowerCase() === 'n' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName) && !e.metaKey && !e.ctrlKey) {
      modal(true);
    }
    if (e.key === 'Escape') modal(false);
  });

  // Feed selector buttons
  $$('[data-feed]').forEach(b => {
    b.onclick = () => {
      $$('[data-feed]').forEach(x => {
        x.classList.remove('active');
        x.setAttribute('aria-pressed', 'false');
      });
      b.classList.add('active');
      b.setAttribute('aria-pressed', 'true');
      refreshWorld(b.dataset.feed);
    };
  });

  // Feed filters
  $$('.feed-filters button').forEach(b => {
    b.onclick = () => {
      $$('.feed-filters button').forEach(x => x.classList.remove('selected'));
      b.classList.add('selected');
      state.filter = b.dataset.filter;
      renderFeed();
    };
  });

  $('#globe-toggle').onclick = () => {
    state.paused = !state.paused;
    $('#globe-toggle').textContent = state.paused ? '▶' : 'Ⅱ';
  };
  $('#reset-view').onclick = () => {
    state.angle = -8; state.tilt = 12; state.zoom = 1;
    toast('Planet viewport reset');
  };
  $$('.quick-prompts button').forEach(b => {
    b.onclick = () => {
      $('#chat-input').value = b.dataset.prompt;
      $('#chat-input').focus();
    };
  });

  // Orchestration actions
  $('#mission-form').onsubmit = e => {
    e.preventDefault();
    const obj = $('#mission-objective').value.trim();
    if (obj) decomposeMission(obj);
  };
  $('#run-mission-btn').onclick = () => {
    switchTab('orchestration');
    $('#mission-objective').focus();
  };
  $('#step-dag-btn').onclick = stepGraph;

  // MCP & Evidence actions
  $('#refresh-approvals').onclick = loadApprovals;
  $('#refresh-evidence').onclick = loadEvidence;
  $('#run-adv-benchmark').onclick = runAdversarialBenchmark;
}

async function boot() {
  attachEvents();
  resize();
  new ResizeObserver(resize).observe(canvas);
  renderGlobe();

  $('#date-label').textContent = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
  function tick() {
    $('#clock').textContent = new Date().toISOString().slice(11, 19) + ' UTC';
  }
  tick();
  setInterval(tick, 1000);

  try {
    await refreshAgents();
    selectAgent('master');
  } catch (e) {
    toast('Agent registry unavailable: ' + e.message);
  }

  loadStatus();
  refreshWorld('seismic');
  setInterval(() => refreshWorld(state.currentFeed), 120000);
}

boot();
