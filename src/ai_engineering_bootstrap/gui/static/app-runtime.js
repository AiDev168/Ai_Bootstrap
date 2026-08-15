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

    function formPayload() {
        return {
            provider: providerInput?.value || "mock",
            model: modelInput?.value.trim() || "",
            base_url: baseUrlInput?.value.trim() || "",
            api_key: apiKeyInput?.value || "",
            preserve_api_key: true,
        };
    }

    function setServerState(online) {
        if (!serverIndicator) return;
        serverIndicator.className = online ? "conn ok" : "conn bad";
        serverIndicator.textContent = online ? "Server: connected" : "Server: offline";
    }

    function setProviderFields() {
        const provider = providerInput?.value || "mock";
        if (baseUrlInput) baseUrlInput.disabled = provider === "mock" || provider === "in_process";
        if (apiKeyInput) apiKeyInput.disabled = false;
        if (modelInput) modelInput.disabled = false;
    }

    function selectedTools() {
        return [...document.querySelectorAll('#create input[type="checkbox"]:checked')]
            .filter(input => input.id !== "force-install")
            .map(input => input.value?.trim())
            .filter(Boolean);
    }

    window.selectedTools = selectedTools;

    function humanSessionLabel(session) {
        return session?.label || session?.request?.natural_language_goal || "Environment Bootstrap";
    }

    function replaceSessionIdsWithLabels(sessions) {
        const root = document.getElementById("sessions-list");
        if (!root) return;
        const labels = new Map((sessions || []).map(item => [item.session_id, humanSessionLabel(item)]));
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

    const originalLoadSessions = window.loadSessions;
    if (typeof originalLoadSessions === "function") {
        window.loadSessions = async function loadSessionsWithLabels() {
            const result = await originalLoadSessions();
            try {
                const payload = await window.api("/sessions");
                replaceSessionIdsWithLabels(payload.sessions || []);
            } catch (_) {
                // Preserve the original session view if relabeling fails.
            }
            return result;
        };
    }

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

    function showResult(payload, success = payload?.ok === true) {
        if (!llmResult) return;
        llmResult.innerHTML = success
            ? `<div class="success-box">${payload?.message || "Connection successful."}</div>`
            : `<div class="error-box">${payload?.message || "Connection failed."}</div>`;
    }

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
            if (payload.ok) {
                showResult({ ok: true, message: `${payload.models?.length || 0} model(s) available. Select or enter the desired model, then Save Settings.` });
            } else {
                showResult(payload, false);
            }
        } catch (error) {
            showResult({ ok: false, message: error.message }, false);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Load Models";
            }
        }
    }

    function annotateNoWork(plan) {
        const detail = document.getElementById("session-detail");
        if (!detail || (plan?.plan?.actions || []).length) return;
        detail.querySelectorAll("[data-start]").forEach(button => {
            button.disabled = true;
            button.title = "No actions are required for the selected desired state.";
        });
        const execution = detail.querySelector("[data-start]")?.closest(".card");
        if (execution && !execution.querySelector("[data-no-work]")) {
            const message = document.createElement("div");
            message.dataset.noWork = "1";
            message.className = "muted";
            message.style.marginTop = "10px";
            message.textContent = "No installation actions are required for the reconciled desired state.";
            execution.appendChild(message);
        }
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
        const rows = history.map(item => {
            const status = item.success ? "success" : "failed";
            return `<div class="event ${status}"><strong>${item.action_id}</strong><br><span>${item.output || item.error || "No execution message."}</span><br><small>${item.timestamp || ""}</small></div>`;
        }).join("");
        card.innerHTML = `<h3>Execution Evidence</h3>${rows || '<div class="muted">No execution evidence recorded yet.</div>'}`;
    }

    window.api = async function apiWithConnectionState(path, method = "GET", body = null) {
        try {
            const result = await originalApi(path, method, body);
            setServerState(true);
            return result;
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
            if (llmResult) llmResult.innerHTML = "<div class=\"success-box\">Settings saved. They persist across server restarts and will be used by new sessions.</div>";
            if (apiKeyInput) apiKeyInput.value = "";
            await window.loadLlm();
            if (typeof window.refreshHealth === "function") await window.refreshHealth();
            if (typeof window.loadSessions === "function") await window.loadSessions();
            return payload;
        } catch (error) {
            showResult({ ok: false, message: error.message }, false);
        }
    };

    window.testLlm = async function testLlmRuntime() {
        try {
            const payload = await window.api("/llm/test", "POST", formPayload());
            showResult(payload, payload.ok === true);
            return payload;
        } catch (error) {
            showResult({ ok: false, message: error.message }, false);
        }
    };

    window.createSession = async function createSessionRuntime() {
        const goal = document.getElementById("goal")?.value.trim() || "";
        const projectPath = document.getElementById("project-path")?.value.trim() || null;
        const button = document.getElementById("create-btn");
        if (!goal) {
            showError("Enter an environment goal first.");
            return;
        }
        if (button) {
            button.disabled = true;
            button.textContent = "Creating…";
        }
        try {
            const tools = selectedTools();
            const forceInstall = Boolean(document.getElementById("force-install")?.checked);
            const payload = {
                natural_language_goal: goal,
                project_path: projectPath,
                required_tools: tools,
                optional_tools: [],
                project_dependencies: [],
                constraints: forceInstall ? { force_install: true } : {},
            };
            const result = await window.api("/sessions", "POST", payload);
            window.openTab("sessions");
            await window.loadSessions();
            await window.viewSession(result.session_id);
        } catch (error) {
            showError(error.message);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Create Session";
            }
        }
    };

    window.renderSession = function renderSessionRuntime(session, stateData, plan, events, decisions) {
        const scrollY = window.scrollY;
        originalRenderSession(session, stateData, plan, events, decisions);
        annotateNoWork(plan);
        renderExecutionHistory(session);
        window.scrollTo({ top: scrollY, left: 0, behavior: "auto" });
    };

    providerInput?.addEventListener("change", () => {
        setProviderFields();
        if (llmResult) llmResult.innerHTML = "<div class=\"muted\">Provider changed. Nothing is saved until you click Save Settings.</div>";
    });

    ensureModelTools();
    ensureInstallControl();
    setProviderFields();
})();
