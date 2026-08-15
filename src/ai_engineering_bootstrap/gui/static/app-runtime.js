"use strict";

(() => {
    const modelInput = document.getElementById("model");
    const baseUrlInput = document.getElementById("base-url");
    const apiKeyInput = document.getElementById("api-key");
    const providerInput = document.getElementById("provider");
    const llmResult = document.getElementById("llm-result");
    const serverIndicator = document.getElementById("server");
    const originalApi = window.api;
    const originalRenderSession = window.renderSession;
    const state = window.state || {};
    state.requestFilter = state.requestFilter || "ALL";
    state.latestPaused = Boolean(state.latestPaused);
    state.requests = state.requests || [];

    window.state = state;

    function formPayload() {
        return {
            provider: providerInput?.value || "mock",
            model: modelInput?.value.trim() || "",
            base_url: baseUrlInput?.value.trim() || "",
            api_key: apiKeyInput?.value || "",
        };
    }

    function setServerState(online) {
        if (!serverIndicator) return;
        serverIndicator.className = online ? "conn ok" : "conn bad";
        serverIndicator.textContent = online ? "Server: connected" : "Server: offline";
    }

    function setProviderFields() {
        if (baseUrlInput) baseUrlInput.disabled = false;
        if (apiKeyInput) apiKeyInput.disabled = false;
        if (modelInput) modelInput.disabled = false;
    }

    function selectedTools() {
        return [...document.querySelectorAll('#create input[type="checkbox"]:checked')]
            .filter(input => input.id !== "force-install")
            .map((input) => input.value?.trim())
            .filter(Boolean);
    }

    window.selectedTools = selectedTools;

    function ensureModelTools() {
        if (!modelInput || document.getElementById("load-models-btn")) return;
        const button = document.createElement("button");
        button.id = "load-models-btn";
        button.type = "button";
        button.className = "secondary";
        button.textContent = "Load Models";
        button.addEventListener("click", loadModels);
        modelInput.insertAdjacentElement("afterend", button);
        const list = document.createElement("datalist");
        list.id = "llm-model-list";
        document.body.appendChild(list);
        modelInput.setAttribute("list", "llm-model-list");
    }

    function ensureInstallControl() {
        if (document.getElementById("force-install")) return;
        const projectPath = document.getElementById("project-path");
        if (!projectPath) return;
        const label = document.createElement("label");
        label.className = "check";
        label.style.marginTop = "12px";
        label.innerHTML = '<input id="force-install" type="checkbox" value="force-install"> Install / repair selected tools even if currently detected';
        projectPath.insertAdjacentElement("afterend", label);
    }

    function ensureConsoleTools() {
        const consolePanel = document.getElementById("console");
        const latest = document.getElementById("latest");
        if (!consolePanel || !latest) return;
        const toolbar = consolePanel.querySelector(".toolbar");
        if (toolbar && !document.getElementById("request-filter")) {
            const filter = document.createElement("select");
            filter.id = "request-filter";
            filter.style.width = "auto";
            filter.innerHTML = '<option value="ALL">All</option><option value="GET">GET</option><option value="POST">POST</option><option value="ERROR">Errors</option>';
            filter.addEventListener("change", () => {
                state.requestFilter = filter.value;
                renderLog();
            });
            toolbar.appendChild(filter);
            const pause = document.createElement("button");
            pause.id = "pause-latest";
            pause.className = "secondary";
            pause.type = "button";
            pause.textContent = "Pause Latest";
            pause.addEventListener("click", () => {
                state.latestPaused = !state.latestPaused;
                pause.textContent = state.latestPaused ? "Resume Latest" : "Pause Latest";
            });
            toolbar.appendChild(pause);
        }
    }

    function renderLog() {
        const root = document.getElementById("request-log");
        if (!root) return;
        const filter = state.requestFilter || "ALL";
        const rows = state.requests.filter((item) => filter === "ALL" || (filter === "ERROR" ? !(item.status >= 200 && item.status < 300) : item.method === filter));
        if (!rows.length) {
            root.innerHTML = '<div class="muted">No matching requests.</div>';
            return;
        }
        root.innerHTML = rows.map((item) => {
            const isError = item.status === 0 || item.status < 200 || item.status >= 400;
            const className = isError ? "bad" : item.status >= 200 && item.status < 300 ? "ok" : "busy";
            return `<div class="request ${className}"><strong>${item.method}</strong> ${item.path}<div class="small">${item.status || "network"} • ${item.ms}ms • ${item.time}</div></div>`;
        }).join("");
    }

    function logRequest(method, path, status, ms, response) {
        state.requests.unshift({ method, path, status, ms, time: new Date().toLocaleTimeString() });
        state.requests = state.requests.slice(0, 120);
        renderLog();
        const latest = document.getElementById("latest");
        if (!latest || state.latestPaused) return;
        latest.textContent = JSON.stringify(response, null, 2);
        latest.classList.toggle("error-box", status === 0 || status >= 400);
    }

    window.api = async function apiWithObservability(path, method = "GET", body = null) {
        const started = performance.now();
        try {
            const options = { method, headers: { "Content-Type": "application/json" } };
            if (body !== null) options.body = JSON.stringify(body);
            const response = await fetch((window.apiBase || "/api/v1") + path, options);
            const text = await response.text();
            let payload = null;
            try {
                payload = text ? JSON.parse(text) : null;
            } catch {
                payload = text;
            }
            const ms = Math.round(performance.now() - started);
            logRequest(method, (window.apiBase || "/api/v1") + path, response.status, ms, payload);
            setServerState(true);
            if (!response.ok) throw new Error(payload?.error || payload?.message || `HTTP ${response.status}`);
            return payload;
        } catch (error) {
            const ms = Math.round(performance.now() - started);
            if (!state.requests.length || state.requests[0].path !== (window.apiBase || "/api/v1") + path || state.requests[0].status !== 0) {
                logRequest(method, (window.apiBase || "/api/v1") + path, 0, ms, { error: error.message });
            }
            setServerState(false);
            throw error;
        }
    };

    window.refreshHealth = async function refreshHealthRuntime() {
        try {
            const health = await window.api("/health");
            let connection = { ok: false, message: "Not tested." };
            try {
                connection = await window.api("/llm/test");
            } catch (error) {
                connection = { ok: false, message: error.message };
            }
            document.getElementById("health").innerHTML = typeof window.badge === "function" ? window.badge(health.status) : health.status;
            document.getElementById("llm").innerHTML = typeof window.badge === "function" ? window.badge(connection.ok === true) : String(connection.ok === true);
            document.getElementById("server").textContent = "Server: connected";
            document.getElementById("server").className = "conn ok";
            const data = health.llm || {};
            const details = document.getElementById("llm-details");
            if (details) {
                details.innerHTML = `<p><strong>Provider:</strong> ${data.provider || "—"}</p><p><strong>Model:</strong> ${data.model || "—"}</p><p><strong>Base URL:</strong> ${data.base_url || "—"}</p><p><strong>Enabled:</strong> ${typeof window.badge === "function" ? window.badge(data.enabled) : data.enabled}</p><p><strong>Connection:</strong> ${typeof window.badge === "function" ? window.badge(connection.ok === true) : connection.ok}</p><p><strong>API key:</strong> ${typeof window.badge === "function" ? window.badge(data.api_key_configured) : data.api_key_configured}</p><p class="small">${connection.message || ""}</p>`;
            }
            return health;
        } catch (error) {
            setServerState(false);
            throw error;
        }
    };

    window.loadLlm = async function loadLlmRuntime() {
        try {
            const settings = await window.api("/llm/settings");
            if (providerInput) providerInput.value = settings.provider || "mock";
            if (modelInput) modelInput.value = settings.model || "";
            if (baseUrlInput) baseUrlInput.value = settings.base_url || "";
            if (apiKeyInput) apiKeyInput.value = "";
            setProviderFields();
            ensureModelTools();
            ensureInstallControl();
            ensureConsoleTools();
            const details = document.getElementById("llm-details");
            if (details) {
                details.innerHTML = `<p><strong>Provider:</strong> ${settings.provider}</p><p><strong>Model:</strong> ${settings.model || "—"}</p><p><strong>Base URL:</strong> ${settings.base_url || "—"}</p><p><strong>Enabled:</strong> ${typeof window.badge === "function" ? window.badge(settings.enabled) : settings.enabled}</p><p><strong>API key:</strong> ${typeof window.badge === "function" ? window.badge(settings.api_key_configured) : settings.api_key_configured}</p>`;
            }
        } catch (error) {
            const details = document.getElementById("llm-details");
            if (details) details.innerHTML = `<div class="error-box">${error.message}</div>`;
        }
    };

    window.saveLlm = async function saveLlmRuntime() {
        try {
            const payload = await window.api("/llm/settings", "POST", formPayload());
            if (llmResult) llmResult.innerHTML = '<div class="success-box">Settings saved. New sessions will use this provider configuration.</div>';
            if (apiKeyInput) apiKeyInput.value = "";
            await window.loadLlm();
            await window.refreshHealth();
            return payload;
        } catch (error) {
            if (llmResult) llmResult.innerHTML = `<div class="error-box">${error.message}</div>`;
            return null;
        }
    };

    window.testLlm = async function testLlmRuntime() {
        try {
            const payload = await window.api("/llm/test", "POST", formPayload());
            if (llmResult) llmResult.innerHTML = payload.ok
                ? `<div class="success-box">${payload.message || "Connection successful."}</div>`
                : `<div class="error-box">${payload.message || "Connection failed."}</div>`;
            return payload;
        } catch (error) {
            if (llmResult) llmResult.innerHTML = `<div class="error-box">${error.message}</div>`;
            return null;
        }
    };

    async function loadModels() {
        const button = document.getElementById("load-models-btn");
        if (button) {
            button.disabled = true;
            button.textContent = "Loading…";
        }
        try {
            const payload = await window.api("/llm/models", "POST", formPayload());
            const list = document.getElementById("llm-model-list");
            if (list) {
                list.innerHTML = "";
                for (const model of payload.models || []) {
                    const option = document.createElement("option");
                    option.value = model;
                    list.appendChild(option);
                }
            }
            if (llmResult) llmResult.innerHTML = payload.ok
                ? `<div class="success-box">${payload.models?.length || 0} model(s) available. Select or enter one, then Save Settings.</div>`
                : `<div class="error-box">${payload.message || "Model discovery failed."}</div>`;
        } catch (error) {
            if (llmResult) llmResult.innerHTML = `<div class="error-box">${error.message}</div>`;
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Load Models";
            }
        }
    }

    function humanSessionLabel(session) {
        return session?.request?.natural_language_goal || session?.label || "Environment Bootstrap";
    }

    function replaceSessionIdsWithLabels(sessions) {
        const root = document.getElementById("sessions-list");
        if (!root) return;
        const labels = new Map((sessions || []).map((item) => [item.session_id, humanSessionLabel(item)]));
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        for (const node of nodes) {
            let value = node.nodeValue || "";
            for (const [sessionId, label] of labels) {
                if (value.includes(sessionId)) value = value.split(sessionId).join(label);
            }
            node.nodeValue = value;
        }
    }

    const originalCreateSession = window.createSession;
    if (typeof originalCreateSession === "function") {
        window.createSession = async function createSessionRuntime() {
            const goal = document.getElementById("goal")?.value.trim() || "";
            const projectPath = document.getElementById("project-path")?.value.trim() || null;
            const forceInstall = Boolean(document.getElementById("force-install")?.checked);
            if (!goal) {
                if (typeof window.showError === "function") window.showError("Enter an environment goal first.");
                return null;
            }
            const button = document.getElementById("create-btn");
            if (button) { button.disabled = true; button.textContent = "Creating…"; }
            try {
                const payload = {
                    natural_language_goal: goal,
                    project_path: projectPath,
                    required_tools: typeof window.selectedTools === "function" ? window.selectedTools() : [],
                    optional_tools: [],
                    project_dependencies: [],
                    constraints: forceInstall ? { force_install: true } : {}
                };
                const created = await window.api("/sessions", "POST", payload);
                window.state.sessionId = created.session_id;
                if (typeof window.openTab === "function") window.openTab("sessions");
                if (typeof window.loadSessions === "function") await window.loadSessions();
                if (typeof window.viewSession === "function") await window.viewSession(created.session_id);
                return created;
            } catch (error) {
                if (typeof window.showError === "function") window.showError(error.message);
                return null;
            } finally {
                if (button) { button.disabled = false; button.textContent = "Create Session"; }
            }
        };
    }

    const originalLoadSessions = window.loadSessions;
    if (typeof originalLoadSessions === "function") {
        window.loadSessions = async function loadSessionsWithLabels() {
            const result = await originalLoadSessions();
            try {
                const payload = await window.api("/sessions");
                replaceSessionIdsWithLabels(payload.sessions || []);
            } catch {
                // Preserve the original session view if relabeling fails.
            }
            return result;
        };
    }

    function renderExecutionHistory(session) {
        const detail = document.getElementById("session-detail");
        if (!detail) return;
        let card = detail.querySelector("[data-execution-evidence]");
        if (!card) {
            card = document.createElement("div");
            card.dataset.executionEvidence = "1";
            card.className = "card";
            detail.appendChild(card);
        }
        const history = session?.execution_history || [];
        const rows = history.map((item) => {
            const failed = item.success === false;
            const details = item.details ? `<pre>${JSON.stringify(item.details, null, 2)}</pre>` : "";
            return `<div class="event ${failed ? "bad" : "ok"}"><strong>${item.action_id}</strong><br><span>${item.output || item.error || "No execution message."}</span>${details}<br><small>${item.timestamp || ""}</small></div>`;
        }).join("");
        card.innerHTML = `<h3>Execution Evidence</h3>${rows || '<div class="muted">No execution evidence recorded yet.</div>'}`;
    }

    window.renderSession = function renderSessionRuntime(session, stateData, plan, events, decisions) {
        const scrollY = window.scrollY;
        originalRenderSession(session, stateData, plan, events, decisions);
        const title = document.querySelector("#session-detail h3");
        if (title) title.textContent = humanSessionLabel(session);
        renderExecutionHistory(session);
        window.scrollTo({ top: scrollY, left: 0, behavior: "auto" });
    };

    function ensureControls() {
        setProviderFields();
        ensureModelTools();
        ensureInstallControl();
        ensureConsoleTools();
    }

    providerInput?.addEventListener("change", () => {
        setProviderFields();
        if (llmResult) llmResult.innerHTML = '<div class="muted">Provider changed. Nothing is saved until you click Save Settings.</div>';
    });

    ensureControls();
    setTimeout(() => {
        if (typeof window.refreshAll === "function") {
            window.refreshAll().catch(() => {});
        }
    }, 0);
})();
