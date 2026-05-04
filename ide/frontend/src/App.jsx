import Editor from "@monaco-editor/react";
import {
  Bot,
  Bug,
  Download,
  File,
  Folder,
  FolderOpen,
  Pencil,
  Play,
  RefreshCw,
  Save,
  SearchCode,
  Send,
  Sparkles,
  TerminalSquare,
  Wand2,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";

const ENV_API_BASE = import.meta.env.VITE_API_BASE || "";
const LOCAL_API_BASE = "http://127.0.0.1:8787";
const LEGACY_API_BASES = new Set(["https://pubs-game-endorsed-seats.trycloudflare.com"]);
const PRESET_PROMPTS = [
  { label: "Dungeon", prompt: "build a 3D dungeon game with bosses" },
  { label: "Platformer", prompt: "build a 2D pygame platformer with enemies and a boss" },
  { label: "FPS", prompt: "build a browser FPS prototype with weapons and target AI" },
  { label: "Puzzle", prompt: "build a puzzle game with board logic and win conditions" },
];
const DEFAULT_LAYOUT = {
  sidebarWidth: 360,
  previewWidth: 460,
  terminalHeight: 280,
  chatHeight: 460,
};
const LAYOUT_LIMITS = {
  sidebarMin: 300,
  sidebarMax: 560,
  previewMin: 320,
  previewMax: 820,
  editorMin: 420,
  gridHandles: 16,
  terminalMin: 190,
  terminalMax: 460,
  chatMin: 360,
  chatMax: 660,
};

async function api(path, options = {}) {
  const apiBase = getApiBase();
  const token = getApiToken();
  if (!apiBase) {
    throw new Error("Backend URL is not configured. Enter a public backend URL, or run the local IDE with the backend on port 8787.");
  }
  const headers = {
    ...(token ? { "X-OmniGameDev-Token": token } : {}),
    ...(options.headers || {}),
  };
  if (options.body || (options.method && options.method !== "GET")) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${apiBase}${path}`, {
    headers,
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function getApiBase() {
  if (typeof window === "undefined") return ENV_API_BASE || LOCAL_API_BASE;
  const saved = window.localStorage.getItem("omnigamedev.apiBase") || "";
  if (saved && ENV_API_BASE && LEGACY_API_BASES.has(saved)) {
    window.localStorage.setItem("omnigamedev.apiBase", ENV_API_BASE);
    return ENV_API_BASE;
  }
  return saved || defaultApiBase();
}

function getApiToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("omnigamedev.apiToken") || "";
}

function defaultApiBase() {
  if (ENV_API_BASE) return ENV_API_BASE;
  if (typeof window === "undefined") return LOCAL_API_BASE;
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1" || host === "::1") return LOCAL_API_BASE;
  return "";
}

function clamp(value, min, max) {
  const upper = Math.max(min, max);
  return Math.min(upper, Math.max(min, value));
}

function normalizeLayout(layout, viewportWidth, viewportHeight) {
  const width = Number.isFinite(viewportWidth)
    ? viewportWidth
    : typeof window === "undefined"
      ? 1440
      : window.innerWidth;
  const height = Number.isFinite(viewportHeight)
    ? viewportHeight
    : typeof window === "undefined"
      ? 900
      : window.innerHeight;

  const sidebarMax = Math.min(
    LAYOUT_LIMITS.sidebarMax,
    Math.max(
      LAYOUT_LIMITS.sidebarMin,
      width - LAYOUT_LIMITS.previewMin - LAYOUT_LIMITS.editorMin - LAYOUT_LIMITS.gridHandles,
    ),
  );
  let sidebarWidth = clamp(Number(layout.sidebarWidth) || DEFAULT_LAYOUT.sidebarWidth, LAYOUT_LIMITS.sidebarMin, sidebarMax);

  const previewMax = Math.min(
    LAYOUT_LIMITS.previewMax,
    Math.max(
      LAYOUT_LIMITS.previewMin,
      width - sidebarWidth - LAYOUT_LIMITS.editorMin - LAYOUT_LIMITS.gridHandles,
    ),
  );
  const previewWidth = clamp(Number(layout.previewWidth) || DEFAULT_LAYOUT.previewWidth, LAYOUT_LIMITS.previewMin, previewMax);

  const correctedSidebarMax = Math.min(
    LAYOUT_LIMITS.sidebarMax,
    Math.max(
      LAYOUT_LIMITS.sidebarMin,
      width - previewWidth - LAYOUT_LIMITS.editorMin - LAYOUT_LIMITS.gridHandles,
    ),
  );
  sidebarWidth = clamp(sidebarWidth, LAYOUT_LIMITS.sidebarMin, correctedSidebarMax);

  return {
    sidebarWidth,
    previewWidth,
    terminalHeight: clamp(
      Number(layout.terminalHeight) || DEFAULT_LAYOUT.terminalHeight,
      LAYOUT_LIMITS.terminalMin,
      Math.min(LAYOUT_LIMITS.terminalMax, Math.max(LAYOUT_LIMITS.terminalMin, height - 280)),
    ),
    chatHeight: clamp(
      Number(layout.chatHeight) || DEFAULT_LAYOUT.chatHeight,
      LAYOUT_LIMITS.chatMin,
      Math.min(LAYOUT_LIMITS.chatMax, Math.max(LAYOUT_LIMITS.chatMin, height - 220)),
    ),
  };
}

function loadLayout() {
  if (typeof window === "undefined") return DEFAULT_LAYOUT;
  try {
    const saved = { ...DEFAULT_LAYOUT, ...JSON.parse(window.localStorage.getItem("omnigamedev.layout") || "{}") };
    return normalizeLayout(saved);
  } catch {
    return normalizeLayout(DEFAULT_LAYOUT);
  }
}

function languageForPath(path = "") {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "javascript";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".css")) return "css";
  if (path.endsWith(".html")) return "html";
  if (path.endsWith(".cs")) return "csharp";
  if (path.endsWith(".cpp") || path.endsWith(".hpp") || path.endsWith(".h")) return "cpp";
  if (path.endsWith(".md")) return "markdown";
  return "plaintext";
}

function firstFile(nodes) {
  for (const node of nodes || []) {
    if (node.type === "file") return node.path;
    const child = firstFile(node.children);
    if (child) return child;
  }
  return "";
}

function FileTree({ nodes, selectedPath, onSelect }) {
  return (
    <div className="tree">
      {nodes.map((node) => (
        <TreeNode key={node.path || node.name} node={node} selectedPath={selectedPath} onSelect={onSelect} />
      ))}
    </div>
  );
}

function TreeNode({ node, selectedPath, onSelect }) {
  const [open, setOpen] = useState(true);
  if (node.type === "directory") {
    return (
      <div className="treeGroup">
        <button className="treeItem dir" onClick={() => setOpen((value) => !value)} title={open ? "Collapse folder" : "Expand folder"}>
          <Folder size={15} />
          <span>{node.name}</span>
        </button>
        {open && (
          <div className="treeChildren">
            {(node.children || []).map((child) => (
              <TreeNode key={child.path || child.name} node={child} selectedPath={selectedPath} onSelect={onSelect} />
            ))}
          </div>
        )}
      </div>
    );
  }
  return (
    <button
      className={`treeItem ${selectedPath === node.path ? "active" : ""}`}
      onClick={() => onSelect(node.path)}
      title={node.path}
    >
      <File size={14} />
      <span>{node.name}</span>
    </button>
  );
}

function TerminalOutput({ output }) {
  return (
    <pre className="terminalText">
      {output || "Terminal output will appear here."}
    </pre>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("build a 3D dungeon game with bosses");
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState("");
  const [tree, setTree] = useState([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [content, setContent] = useState("");
  const [terminal, setTerminal] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [backendUrl, setBackendUrl] = useState(getApiBase());
  const [backendToken, setBackendToken] = useState(getApiToken());
  const [backendStatus, setBackendStatus] = useState("checking");
  const [layout, setLayout] = useState(loadLayout);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "OmniGameDev AI is online." },
  ]);
  const [busy, setBusy] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now());

  const previewUrl = useMemo(() => {
    if (!currentProject) return "";
    return `${backendUrl}/api/projects/${encodeURIComponent(currentProject)}/preview/?t=${previewKey}`;
  }, [backendUrl, currentProject, previewKey]);

  useEffect(() => {
    initializeBackend();
  }, []);

  useEffect(() => {
    window.localStorage.setItem("omnigamedev.layout", JSON.stringify(layout));
  }, [layout]);

  useEffect(() => {
    function onWindowResize() {
      setLayout((current) => normalizeLayout(current));
    }

    window.addEventListener("resize", onWindowResize);
    return () => window.removeEventListener("resize", onWindowResize);
  }, []);

  function startResize(kind, event) {
    event.preventDefault();
    document.body.classList.add("resizing");

    function onMove(moveEvent) {
      setLayout((current) => {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const next = { ...current };
        if (kind === "sidebar") {
          next.sidebarWidth = moveEvent.clientX;
          return normalizeLayout(next, viewportWidth, viewportHeight);
        }
        if (kind === "preview") {
          next.previewWidth = viewportWidth - moveEvent.clientX;
          return normalizeLayout(next, viewportWidth, viewportHeight);
        }
        if (kind === "terminal") {
          next.terminalHeight = viewportHeight - moveEvent.clientY;
          return normalizeLayout(next, viewportWidth, viewportHeight);
        }
        if (kind === "chat") {
          next.chatHeight = viewportHeight - moveEvent.clientY;
          return normalizeLayout(next, viewportWidth, viewportHeight);
        }
        return current;
      });
    }

    function onUp() {
      document.body.classList.remove("resizing");
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
  }

  async function initializeBackend() {
    const ready = await checkBackend();
    if (ready) {
      await refreshProjects();
    }
  }

  async function checkBackend() {
    if (!getApiBase()) {
      setBackendStatus("offline");
      return false;
    }
    try {
      const health = await api("/api/health");
      if (health.auth_required && !getApiToken()) {
        setBackendStatus("locked");
        return false;
      }
      setBackendStatus("online");
      return true;
    } catch {
      setBackendStatus("offline");
      return false;
    }
  }

  async function applyBackendUrl() {
    const clean = backendUrl.trim().replace(/\/$/, "") || defaultApiBase();
    const cleanToken = backendToken.trim();
    window.localStorage.setItem("omnigamedev.apiBase", clean);
    window.localStorage.setItem("omnigamedev.apiToken", cleanToken);
    setBackendUrl(clean);
    setBackendToken(cleanToken);
    setBackendStatus("checking");
    const ready = await checkBackend();
    if (ready) {
      await refreshProjects();
    }
  }

  async function refreshProjects() {
    if (!getApiBase()) {
      setProjects([]);
      return;
    }
    try {
      const rows = await api("/api/projects");
      setProjects(rows);
      if (!currentProject && rows[0]) {
        await openProject(rows[0].name);
      }
    } catch (error) {
      setTerminal(String(error.message || error));
    }
  }

  async function openProject(name) {
    setCurrentProject(name);
    const nextTree = await api(`/api/projects/${encodeURIComponent(name)}/tree`);
    setTree(nextTree);
    const path = firstFile(nextTree);
    if (path) {
      await openFile(name, path);
    }
    setPreviewKey(Date.now());
  }

  async function openFile(projectName, path) {
    const project = projectName || currentProject;
    if (!project || !path) return;
    const result = await api(`/api/projects/${encodeURIComponent(project)}/file?path=${encodeURIComponent(path)}`);
    setSelectedFile(result.path);
    setContent(result.content);
  }

  async function generate() {
    if (!prompt.trim()) return;
    setBusy(true);
    setMessages((rows) => [...rows, { role: "user", content: prompt }]);
    setTerminal("Planning and generating project...");
    try {
      const result = await api("/api/generate", {
        method: "POST",
        body: JSON.stringify({ prompt, run_after: true }),
      });
      setMessages((rows) => [
        ...rows,
        {
          role: "assistant",
          content: `Generated ${result.project_name} with ${result.plan.engine}.`,
        },
      ]);
      setCurrentProject(result.project_name);
      setTree(result.tree);
      setTerminal(formatExecution(result.execution, result.reasoning_trace, result.fixes));
      const path = firstFile(result.tree);
      if (path) await openFile(result.project_name, path);
      await refreshProjects();
      setPreviewKey(Date.now());
    } catch (error) {
      setMessages((rows) => [...rows, { role: "assistant", content: "Generation failed. Check terminal output." }]);
      setTerminal(String(error.message || error));
    } finally {
      setBusy(false);
    }
  }

  async function saveFile() {
    if (!currentProject || !selectedFile) return;
    setBusy(true);
    try {
      const result = await api(`/api/projects/${encodeURIComponent(currentProject)}/file`, {
        method: "PUT",
        body: JSON.stringify({ path: selectedFile, content }),
      });
      setTree(result.tree);
      setTerminal(`Saved ${selectedFile}`);
      setPreviewKey(Date.now());
    } catch (error) {
      setTerminal(String(error.message || error));
    } finally {
      setBusy(false);
    }
  }

  async function runProject() {
    if (!currentProject) return;
    setBusy(true);
    setTerminal("Running smoke checks...");
    try {
      const result = await api(`/api/projects/${encodeURIComponent(currentProject)}/run`, { method: "POST" });
      setTerminal(formatExecution(result));
      setPreviewKey(Date.now());
    } catch (error) {
      setTerminal(String(error.message || error));
    } finally {
      setBusy(false);
    }
  }

  async function openFolder() {
    if (!folderPath.trim()) return;
    setBusy(true);
    setTerminal("Opening folder into OmniGameDev projects...");
    try {
      const result = await api("/api/open-folder", {
        method: "POST",
        body: JSON.stringify({ folder_path: folderPath.trim() }),
      });
      setMessages((rows) => [...rows, { role: "assistant", content: result.message }]);
      setCurrentProject(result.project_name);
      setTree(result.tree);
      const path = firstFile(result.tree);
      if (path) await openFile(result.project_name, path);
      await refreshProjects();
      setPreviewKey(Date.now());
      setTerminal(result.message);
    } catch (error) {
      setTerminal(String(error.message || error));
    } finally {
      setBusy(false);
    }
  }

  async function runAiAction(mode) {
    if (!currentProject) return;
    setBusy(true);
    const labels = { review: "Reviewing code...", improve: "Improving project...", edit: "Editing selected file..." };
    setTerminal(labels[mode] || "Working...");
    try {
      const result = await api(`/api/projects/${encodeURIComponent(currentProject)}/ai-action`, {
        method: "POST",
        body: JSON.stringify({
          mode,
          prompt,
          path: selectedFile || null,
          content: selectedFile ? content : null,
        }),
      });
      setTree(result.tree || tree);
      if (result.file) {
        setSelectedFile(result.file.path);
        setContent(result.file.content);
      } else if (selectedFile && result.changed_files?.includes(selectedFile)) {
        await openFile(currentProject, selectedFile);
      }
      setTerminal(formatAiAction(result));
      setMessages((rows) => [...rows, { role: "assistant", content: result.message || "AI action complete." }]);
      setPreviewKey(Date.now());
    } catch (error) {
      setTerminal(String(error.message || error));
    } finally {
      setBusy(false);
    }
  }

  function exportZip() {
    if (!currentProject) return;
    const apiBase = getApiBase();
    if (!apiBase) {
      setTerminal("Backend URL is not configured. Enter a public backend URL before exporting.");
      return;
    }
    const token = getApiToken();
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : "";
    window.location.href = `${apiBase}/api/projects/${encodeURIComponent(currentProject)}/zip${tokenQuery}`;
  }

  return (
    <main
      className="ideShell"
      style={{
        "--sidebar-width": `${layout.sidebarWidth}px`,
        "--preview-width": `${layout.previewWidth}px`,
        "--terminal-height": `${layout.terminalHeight}px`,
        "--chat-height": `${layout.chatHeight}px`,
      }}
    >
      <aside className="sidebar">
        <section className="panel filePanel">
          <div className="panelHeader">
            <div className="brand">
              <Sparkles size={17} />
              <span>OmniGameDev AI</span>
            </div>
            <button className="iconButton" onClick={() => { checkBackend(); refreshProjects(); }} title="Refresh projects">
              <RefreshCw size={16} />
            </button>
          </div>
          <div className={`backendStatus ${backendStatus}`}>
            <span>
              {backendStatus === "online"
                ? "Agent backend online"
                : backendStatus === "locked"
                  ? "Access code needed"
                  : backendStatus === "offline"
                    ? "Backend not connected"
                    : "Checking backend"}
            </span>
            <small>{backendUrl || "Enter a public HTTPS backend URL for Vercel"}</small>
            <div className="backendTokenRow">
              <input
                value={backendToken}
                onChange={(event) => setBackendToken(event.target.value)}
                placeholder="Backend access code"
                title="Access code required by public backends"
                type="password"
              />
            </div>
            <div className="backendUrlRow">
              <input
                value={backendUrl}
                onChange={(event) => setBackendUrl(event.target.value)}
                placeholder="http://127.0.0.1:8787 or tunnel URL"
                title="Backend API URL"
              />
              <button type="button" onClick={applyBackendUrl}>Use</button>
            </div>
          </div>
          <select className="projectSelect" value={currentProject} onChange={(event) => openProject(event.target.value)}>
            <option value="">No project</option>
            {projects.map((project) => (
              <option key={project.name} value={project.name}>
                {project.name}
              </option>
            ))}
          </select>
          <div className="openFolderRow">
            <input
              value={folderPath}
              onChange={(event) => setFolderPath(event.target.value)}
              placeholder="C:\\path\\to\\game-folder"
              title="Folder path to import into OmniGameDev"
            />
            <button className="iconTextButton" onClick={openFolder} disabled={busy || !folderPath.trim()} title="Open folder">
              <FolderOpen size={15} />
              <span>Open</span>
            </button>
          </div>
          <FileTree nodes={tree} selectedPath={selectedFile} onSelect={(path) => openFile(currentProject, path)} />
        </section>
        <div className="resizeHandle horizontal chatResize" onPointerDown={(event) => startResize("chat", event)} title="Resize AI chat" />

        <section className="panel chatPanel">
          <div className="panelHeader">
            <div className="panelTitle">
              <Bot size={16} />
              <span>AI Chat</span>
            </div>
          </div>
          <div className="messages">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`message ${message.role}`}>
                {message.content}
              </div>
            ))}
          </div>
          <div className="promptRow">
            <div className="presetStrip" aria-label="Game mode presets">
              {PRESET_PROMPTS.map((preset) => (
                <button key={preset.label} type="button" onClick={() => setPrompt(preset.prompt)}>
                  {preset.label}
                </button>
              ))}
            </div>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={3} />
            <div className="actionGrid">
              <button className="primaryButton" onClick={generate} disabled={busy} title="Generate project">
                <Send size={16} />
                <span>Generate</span>
              </button>
              <button className="iconTextButton" onClick={() => runAiAction("review")} disabled={busy || !currentProject} title="Find mistakes in this project">
                <SearchCode size={16} />
                <span>Review</span>
              </button>
              <button className="iconTextButton" onClick={() => runAiAction("improve")} disabled={busy || !currentProject} title="Improve this project">
                <Wand2 size={16} />
                <span>Improve</span>
              </button>
              <button className="iconTextButton" onClick={() => runAiAction("edit")} disabled={busy || !currentProject || !selectedFile} title="Edit selected file using the prompt">
                <Pencil size={16} />
                <span>Edit File</span>
              </button>
            </div>
          </div>
        </section>
      </aside>
      <div className="resizeHandle vertical sidebarResize" onPointerDown={(event) => startResize("sidebar", event)} title="Resize sidebar" />

      <section className="panel editorPanel">
        <div className="panelHeader">
          <div className="fileCrumb">{selectedFile || "Select a file"}</div>
          <div className="toolbar">
            <button className="iconButton" onClick={saveFile} disabled={busy || !selectedFile} title="Save file">
              <Save size={16} />
            </button>
            <button className="iconButton" onClick={runProject} disabled={busy || !currentProject} title="Run smoke checks">
              <Play size={16} />
            </button>
            <button className="iconButton" onClick={() => runAiAction("review")} disabled={busy || !currentProject} title="Find mistakes">
              <Bug size={16} />
            </button>
            <button className="iconButton" onClick={exportZip} disabled={!currentProject} title="Export ZIP">
              <Download size={16} />
            </button>
          </div>
        </div>
        <Editor
          theme="vs-dark"
          path={selectedFile}
          language={languageForPath(selectedFile)}
          value={content}
          onChange={(value) => setContent(value || "")}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            fontLigatures: true,
            lineNumbersMinChars: 3,
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </section>
      <div className="resizeHandle vertical previewResize" onPointerDown={(event) => startResize("preview", event)} title="Resize preview" />

      <section className="panel previewPanel">
        <div className="panelHeader">
          <div className="panelTitle">
            <Play size={16} />
            <span>Preview</span>
          </div>
          <button className="iconButton" onClick={() => setPreviewKey(Date.now())} disabled={!currentProject} title="Reload preview">
            <RefreshCw size={16} />
          </button>
        </div>
        {previewUrl ? <iframe title="Project preview" src={previewUrl} /> : <div className="emptyPreview">No preview</div>}
      </section>

      <section className="panel terminalPanel">
        <div className="panelHeader">
          <div className="panelTitle">
            <TerminalSquare size={16} />
            <span>Terminal Output</span>
          </div>
        </div>
        <TerminalOutput output={terminal} />
      </section>
      <div className="resizeHandle horizontal terminalResize" onPointerDown={(event) => startResize("terminal", event)} title="Resize terminal" />
    </main>
  );
}

function formatExecution(execution, trace = [], fixes = []) {
  const lines = [];
  if (trace?.length) {
    lines.push("Reasoning summary:");
    trace.forEach((item) => lines.push(`- ${item}`));
    lines.push("");
  }
  if (fixes?.length) {
    lines.push("Self-heal fixes:");
    fixes.forEach((item) => lines.push(`- ${item}`));
    lines.push("");
  }
  if (!execution) {
    lines.push("No execution result.");
    return lines.join("\n");
  }
  lines.push(`Success: ${execution.success}`);
  if (execution.error_summary) lines.push(`Error: ${execution.error_summary}`);
  for (const command of execution.commands || []) {
    lines.push("");
    lines.push(`$ ${command.args.join(" ")}`);
    lines.push(`exit ${command.returncode} in ${command.duration_seconds.toFixed(2)}s`);
    if (command.stdout) lines.push(command.stdout);
    if (command.stderr) lines.push(command.stderr);
  }
  return lines.join("\n");
}

function formatAiAction(result) {
  const lines = [result.message || "AI action complete."];
  if (result.changed_files?.length) {
    lines.push("");
    lines.push("Changed files:");
    result.changed_files.forEach((file) => lines.push(`- ${file}`));
  }
  if (result.findings?.length) {
    lines.push("");
    lines.push("Findings:");
    result.findings.slice(0, 60).forEach((finding) => {
      lines.push(`- [${finding.severity}] ${finding.file}:${finding.line} ${finding.message}`);
    });
  }
  if (result.execution) {
    lines.push("");
    lines.push(formatExecution(result.execution));
  }
  return lines.join("\n");
}
