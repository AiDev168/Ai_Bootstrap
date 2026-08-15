"use strict";

(() => {
  const state = window.state || {};
  state.requests = Array.isArray(state.requests) ? state.requests : [];
  state.requestFilter = state.requestFilter || "ALL";
  state.latestPaused = Boolean(state.latestPaused);
  state.selectedRequestIndex = Number.isInteger(state.selectedRequestIndex) ? state.selectedRequestIndex : -1;
  state.getRequestLimit = 50;
  window.state = state;

  const originalRefreshAll = window.refreshAll;
  const originalRefreshHealth = window.refreshHealth;
  const originalRenderSession = window.renderSession;
  const originalLoadLlm = window.loadLlm;
  const apiBase = window.apiBase || "/api/v1";
  const providerInput = document.getElementById("provider");
  const modelInput = document.getElementById("model");
  const baseUrlInput = document.getElementById("base-url");
  const apiKeyInput = document.getElementById("api-key");
  const llmResult = document.getElementById("llm-result");

  const textMap = {
    "Dashboard": "داشبورد",
    "New Session": "جلسه جدید",
    "Sessions": "جلسه‌ها",
    "LLM Settings": "تنظیمات LLM",
    "Request Console": "کنسول درخواست‌ها",
    "Backend Health": "سلامت Backend",
    "Development Ready": "آمادگی توسعه",
    "Environment Audit": "ممیزی محیط",
    "Run Audit": "اجرای ممیزی",
    "Engineering Tools": "ابزارهای مهندسی",
    "Refresh": "به‌روزرسانی",
    "Quick Actions": "اقدامات سریع",
    "Desired Environment": "محیط مطلوب",
    "Natural-language goal": "هدف به زبان طبیعی",
    "Required tools": "ابزارهای موردنیاز",
    "Project path": "مسیر پروژه",
    "Create Session": "ایجاد جلسه",
    "Reset": "بازنشانی",
    "Lifecycle": "چرخه اجرا",
    "Audit current environment": "۱. ممیزی محیط فعلی",
    "Reconcile Actual vs Desired State": "۲. تطبیق وضعیت فعلی و مطلوب",
    "Generate and validate Execution Plan": "۳. تولید و اعتبارسنجی برنامه اجرا",
    "Review / approve actions": "۴. بازبینی و تأیید اقدامات",
    "Execute through canonical pipeline": "۵. اجرا از طریق پایپ‌لاین اصلی",
    "Verify and record evidence": "۶. تأیید و ثبت شواهد",
    "LLM Connection": "اتصال LLM",
    "Model": "مدل",
    "API key": "کلید API",
    "Save Settings": "ذخیره تنظیمات",
    "Test Connection": "تست اتصال",
    "LLM Status": "وضعیت LLM",
    "Load Models": "بارگذاری مدل‌ها",
    "Latest Response": "آخرین پاسخ",
    "Clear": "پاک‌کردن",
    "All": "همه",
    "Errors": "خطاها",
    "Pause Latest": "توقف آخرین پاسخ",
    "Resume Latest": "ادامه آخرین پاسخ",
    "Execution": "اجرا",
    "Start Safe": "اجرای ایمن",
    "Start Real": "اجرای واقعی",
    "Cancel": "لغو",
    "Timeline": "خط زمانی",
    "Agent Decisions": "تصمیم‌های Agent",
    "Execution Evidence": "شواهد اجرا",
    "Server: connected": "سرور: متصل",
    "Server: offline": "سرور: قطع",
  };

  const style = document.createElement("style");
  style.textContent = `
    .request-console-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    .request-console-toolbar select{width:auto;min-width:110px}
    .request{cursor:pointer}
    .request.selected{outline:2px solid #8fa8ff;outline-offset:1px}
    .request.ok{color:#89e7b7}
    .request.bad{color:#ff9da6}
    .request.busy{color:#f7d58d}
    .latest-empty{color:#91a0b6;font-size:13px}
    .timeline-legend{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
    .timeline-key{padding:4px 8px;border-radius:999px;font-size:11px;background:#0b1424}
    .timeline-event{border-left:3px solid #5d7cff}
    .timeline-event.stage-session{border-color:#8fa8ff}
    .timeline-event.stage-intent{border-color:#b58cff}
    .timeline-event.stage-plan{border-color:#5d7cff}
    .timeline-event.stage-approval{border-color:#f5c76b}
    .timeline-event.stage-execution{border-color:#62d49b}
    .timeline-event.stage-verification{border-color:#4fc3f7}
    .timeline-event.stage-recovery{border-color:#ffb454}
    .timeline-event.stage-error{border-color:#ff7f8b;background:#21121a}
    .lang-switch{display:flex;gap:4px;align-items:center;margin-left:auto}
    .lang-switch button{padding:6px 9px;font-size:11px}
    body.rtl{direction:rtl}
    body.rtl .event,body.rtl .action{border-left:0;border-right:3px solid #5d7cff}
  `;
  document.head.appendChild(style);

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isError(item) {
    return item.status === 0 || item.status < 200 || item.status >= 400;
  }

  function filteredRequests() {
    const filter = state.requestFilter || "ALL";
    return state.requests.filter((item) => {
      if (filter === "ALL") return true;
      if (filter === "ERROR") return isError(item);
      return item.method === filter;
    });
  }

  function renderLatestSelected() {
    const latest = document.getElementById("latest");
    if (!latest) return;
    const item = state.selectedRequestIndex >= 0 ? state.requests[state.selectedRequestIndex] : null;
    if (!item) {
      latest.textContent = "Select a request from the console to inspect its response.";
      latest.className = "latest-empty";
      return;
    }
    latest.textContent = JSON.stringify(item.response ?? item.error ?? {}, null, 2);
    latest.className = isError(item) ? "error-box" : "success-box";
  }

  function renderLog() {
    const root = document.getElementById("request-log");
    if (!root) return;
    const rows = filteredRequests();
    if (!rows.length) {
      root.innerHTML = `<div class="muted">${state.requestFilter === "ERROR" ? "No errors." : "No matching requests."}</div>`;
      return;
    }
    root.innerHTML = rows.map((item) => {
      const index = state.requests.indexOf(item);
      const cssClass = isError(item) ? "bad" : item.status >= 200 && item.status < 300 ? "ok" : "busy";
      const selected = index === state.selectedRequestIndex ? " selected" : "";
      return `<div class="request ${cssClass}${selected}" data-request-index="${index}">
        <strong>${escapeHtml(item.method)}</strong> ${escapeHtml(item.path)}
        <div class="small">${item.status || "network"} • ${item.ms}ms • ${escapeHtml(item.time)}</div>
      </div>`;
    }).join("");
    root.querySelectorAll("[data-request-index]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selectedRequestIndex = Number(row.dataset.requestIndex);
        renderLog();
        renderLatestSelected();
      });
    });
  }

  function ensureConsoleControls() {
    const panel = document.getElementById("console");
    const latest = document.getElementById("latest");
    if (!panel || !latest) return;
    const toolbar = panel.querySelector(".toolbar");
    if (!toolbar) return;
    let tools = toolbar.querySelector(".request-console-toolbar");
    if (!tools) {
      tools = document.createElement("div");
      tools.className = "request-console-toolbar";
      toolbar.appendChild(tools);
    }
    let filter = document.getElementById("request-filter");
    if (!filter) {
      filter = document.createElement("select");
      filter.id = "request-filter";
      filter.innerHTML = '<option value="ALL">All</option><option value="GET">GET</option><option value="POST">POST</option><option value="ERROR">Errors</option>';
      filter.addEventListener("change", () => {
        state.requestFilter = filter.value;
        renderLog();
      });
      tools.appendChild(filter);
    }
    let pause = document.getElementById("pause-latest");
    if (!pause) {
      pause = document.createElement("button");
      pause.id = "pause-latest";
      pause.className = "secondary";
      pause.type = "button";
      pause.textContent = state.latestPaused ? "Resume Latest" : "Pause Latest";
      pause.addEventListener("click", () => {
        state.latestPaused = !state.latestPaused;
        pause.textContent = state.latestPaused ? "Resume Latest" : "Pause Latest";
      });
      tools.appendChild(pause);
    }
    renderLog();
    renderLatestSelected();
  }

  window.logRequest = function logRequest(method, path, status, ms, response) {
    const numericStatus = Number(status) || 0;
    const entry = {
      method,
      path,
      status: numericStatus,
      ms,
      time: new Date().toLocaleTimeString(),
      response: numericStatus >= 200 && numericStatus < 400 ? response : null,
      error: numericStatus < 200 || numericStatus >= 400 ? response : null,
    };
    state.requests.push(entry);

    // Retain all POST requests and every error. Bound only successful GET traffic to 50 records.
    const successfulGets = state.requests.filter((item) => item.method === "GET" && !isError(item));
    if (successfulGets.length > state.getRequestLimit) {
      let remove = successfulGets.length - state.getRequestLimit;
      for (let index = 0; index < state.requests.length && remove > 0; index += 1) {
        const item = state.requests[index];
        if (item.method === "GET" && !isError(item)) {
          if (state.selectedRequestIndex === index) state.selectedRequestIndex = -1;
          state.requests.splice(index, 1);
          index -= 1;
          remove -= 1;
        }
      }
    }

    // A new request never replaces Latest Response. The user must click an item.
    renderLog();
    if (state.selectedRequestIndex < 0) renderLatestSelected();
  };

  window.api = async function apiEnhanced(path, method = "GET", body = null) {
    const started = performance.now();
    const options = { method, headers: { "Content-Type": "application/json" } };
    if (body !== null) options.body = JSON.stringify(body);
    try {
      const response = await fetch(apiBase + path, options);
      const text = await response.text();
      let payload;
      try {
        payload = text ? JSON.parse(text) : null;
      } catch {
        payload = text;
      }
      window.logRequest(method, apiBase + path, response.status, Math.round(performance.now() - started), payload);
      if (!response.ok) {
        throw new Error(payload?.error || payload?.message || payload?.detail || `HTTP ${response.status}`);
      }
      return payload;
    } catch (error) {
      window.logRequest(method, apiBase + path, 0, Math.round(performance.now() - started), { error: error.message });
      throw error;
    }
  };

  window.clearLog = function clearLogEnhanced() {
    state.requests = [];
    state.selectedRequestIndex = -1;
    renderLog();
    renderLatestSelected();
  };

  function addLanguageSwitch() {
    if (document.getElementById("language-switch")) return;
    const server = document.getElementById("server");
    const header = server?.closest(".header");
    if (!header) return;
    const wrapper = document.createElement("div");
    wrapper.id = "language-switch";
    wrapper.className = "lang-switch";
    wrapper.innerHTML = '<button type="button" data-lang="en">EN</button><button type="button" data-lang="fa" class="secondary">FA</button>';
    header.appendChild(wrapper);
    wrapper.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => setLanguage(button.dataset.lang)));
  }

  function translatePage(lang) {
    document.querySelectorAll("body *").forEach((element) => {
      if (element.children.length || element.closest("pre,code,input,textarea,select,option")) return;
      const original = element.dataset.i18nOriginal || element.textContent;
      if (!element.dataset.i18nOriginal) element.dataset.i18nOriginal = original;
      element.textContent = lang === "fa" ? (textMap[original] || original) : original;
    });
    document.documentElement.lang = lang === "fa" ? "fa" : "en";
    document.body.classList.toggle("rtl", lang === "fa");
    localStorage.setItem("gui-language", lang);
  }

  function setLanguage(lang) {
    translatePage(lang);
    renderLog();
    renderLatestSelected();
  }

  function classifyTimelineText(text) {
    const value = String(text || "").toLowerCase();
    if (value.includes("intent")) return "intent";
    if (value.includes("plan")) return "plan";
    if (value.includes("approval") || value.includes("approved") || value.includes("rejected") || value.includes("skipped")) return "approval";
    if (value.includes("verification") || value.includes("verified")) return "verification";
    if (value.includes("recovery") || value.includes("retry")) return "recovery";
    if (value.includes("failed") || value.includes("error")) return "error";
    if (value.includes("started") || value.includes("execution") || value.includes("completed")) return "execution";
    return "session";
  }

  function decorateTimeline(root) {
    const timeline = root?.querySelector?.(".timeline");
    if (!timeline) return;
    if (!timeline.querySelector(".timeline-legend")) {
      const legend = document.createElement("div");
      legend.className = "timeline-legend";
      legend.innerHTML = ["session", "intent", "plan", "approval", "execution", "verification", "recovery", "error"]
        .map((key) => `<span class="timeline-key stage-${key}">${key}</span>`).join("");
      timeline.prepend(legend);
    }
    timeline.querySelectorAll(".event").forEach((event) => event.classList.add("timeline-event", `stage-${classifyTimelineText(event.textContent)}`));
  }

  function addSafeModeHint() {
    document.querySelectorAll('[data-start="safe"]').forEach((button) => {
      button.title = "Safe mode is a dry-run / preview. It does not perform real installation.";
    });
  }

  function enableProviderFields() {
    if (baseUrlInput) baseUrlInput.disabled = false;
    if (modelInput) modelInput.disabled = false;
    if (apiKeyInput) apiKeyInput.disabled = false;
  }

  function ensureModels() {
    if (!modelInput || document.getElementById("load-models-btn")) return;
    const button = document.createElement("button");
    button.id = "load-models-btn";
    button.type = "button";
    button.className = "secondary";
    button.textContent = "Load Models";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const payload = await window.api("/llm/models", "POST", {
          provider: providerInput?.value || "mock",
          model: modelInput?.value.trim() || "",
          base_url: baseUrlInput?.value.trim() || "",
          api_key: apiKeyInput?.value || "",
        });
        modelInput.value = payload.models?.[0] || modelInput.value;
        if (llmResult) llmResult.innerHTML = `<div class="success-box">${payload.models?.length || 0} model(s) discovered. Select or enter one, then save.</div>`;
      } catch (error) {
        if (llmResult) llmResult.innerHTML = `<div class="error-box">${error.message}</div>`;
      } finally {
        button.disabled = false;
      }
    });
    modelInput.insertAdjacentElement("afterend", button);
  }

  window.loadLlm = async function loadLlmEnhanced() {
    const result = await originalLoadLlm();
    enableProviderFields();
    ensureModels();
    return result;
  };

  window.refreshHealth = async function refreshHealthEnhanced() {
    const result = await originalRefreshHealth();
    try {
      const probe = await window.api("/llm/test", "POST", {});
      const llm = document.getElementById("llm");
      if (llm) llm.innerHTML = typeof window.badge === "function" ? window.badge(probe.ok === true) : String(probe.ok === true);
    } catch {
      const llm = document.getElementById("llm");
      if (llm) llm.innerHTML = typeof window.badge === "function" ? window.badge(false) : "false";
    }
    return result;
  };

  window.refreshAll = async function refreshAllEnhanced() {
    const result = await originalRefreshAll();
    ensureConsoleControls();
    decorateTimeline(document.getElementById("session-detail"));
    addSafeModeHint();
    enableProviderFields();
    return result;
  };

  window.renderSession = function renderSessionEnhanced(...args) {
    const scrollY = window.scrollY;
    originalRenderSession(...args);
    decorateTimeline(document.getElementById("session-detail"));
    addSafeModeHint();
    window.scrollTo({ top: scrollY, left: 0, behavior: "auto" });
  };

  providerInput?.addEventListener("change", enableProviderFields);
  addLanguageSwitch();
  ensureConsoleControls();
  ensureModels();
  enableProviderFields();
  setLanguage(localStorage.getItem("gui-language") || "en");
  renderLatestSelected();
})();
