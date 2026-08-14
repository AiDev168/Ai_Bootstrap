"use strict";

(() => {
    const modelInput = document.getElementById("model");
    const baseUrlInput = document.getElementById("base-url");
    const apiKeyInput = document.getElementById("api-key");
    const providerInput = document.getElementById("provider");
    const llmResult = document.getElementById("llm-result");
    const serverIndicator = document.getElementById("server");
    const originalApi = window.api;
    const originalLoadLlm = window.loadLlm;
    const originalSaveLlm = window.saveLlm;
    const originalTestLlm = window.testLlm;

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
        if (apiKeyInput) apiKeyInput.disabled = provider !== "remote_api";
        if (modelInput) modelInput.disabled = false;
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

    providerInput?.addEventListener("change", () => {
        setProviderFields();
        if (llmResult) llmResult.innerHTML = "<div class=\"muted\">Provider changed. Nothing is saved until you click Save Settings.</div>";
    });

    ensureModelTools();
    setProviderFields();
    void originalLoadLlm;
    void originalSaveLlm;
    void originalTestLlm;
})();
