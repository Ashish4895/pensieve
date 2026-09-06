document.addEventListener("DOMContentLoaded", () => {
    const chatHistory = document.getElementById("chat-history");
    const welcomeBox = document.getElementById("welcome-box");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    const settingsBtn = document.getElementById("settings-btn");
    const settingsPanel = document.getElementById("settings-panel");
    const providerSelect = document.getElementById("provider-select");
    const apiKeyInput = document.getElementById("api-key-input");
    const modelInput = document.getElementById("model-input");
    const statusText = document.querySelector(".status-text");
    const pulseDot = document.querySelector(".pulse-dot");
    const suggestionChips = document.querySelectorAll(".suggestion-chip");

    const SESSION_STORAGE_KEY = "byok_session_id";
    let SESSION_ID = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!SESSION_ID) {
        SESSION_ID = crypto.randomUUID
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        sessionStorage.setItem(SESSION_STORAGE_KEY, SESSION_ID);
    }
    const DEFAULT_MODELS = {
        gemini: "gemini-2.5-flash",
        openai: "gpt-4o-mini",
        openrouter: "openai/gpt-4o-mini"
    };
    let sending = false;

    function getCookie(name) {
        const cookie = document.cookie
            .split("; ")
            .find(item => item.startsWith(`${name}=`));
        return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
    }

    providerSelect.value = sessionStorage.getItem("byok_provider") || "gemini";
    apiKeyInput.value = sessionStorage.getItem("byok_api_key") || "";
    modelInput.value = sessionStorage.getItem("byok_model") || DEFAULT_MODELS[providerSelect.value];

    function updateSendState() {
        const hasKey = Boolean(apiKeyInput.value.trim());
        sendBtn.disabled = !hasKey || sending;
        sendBtn.title = hasKey ? "Send message" : "Add an API key in Settings";
        statusText.textContent = hasKey ? "Online" : "Key required";
        pulseDot.classList.toggle("key-required", !hasKey);
    }

    settingsBtn.addEventListener("click", () => {
        const opening = settingsPanel.hidden;
        settingsPanel.hidden = !opening;
        settingsBtn.setAttribute("aria-expanded", String(opening));
    });

    providerSelect.addEventListener("change", () => {
        modelInput.value = DEFAULT_MODELS[providerSelect.value];
        sessionStorage.setItem("byok_provider", providerSelect.value);
        sessionStorage.setItem("byok_model", modelInput.value);
    });

    apiKeyInput.addEventListener("input", () => {
        sessionStorage.setItem("byok_api_key", apiKeyInput.value);
        updateSendState();
    });

    modelInput.addEventListener("input", () => {
        sessionStorage.setItem("byok_model", modelInput.value);
    });

    // Helper to format bot responses (handling basic markdown)
    function formatMessage(text) {
        if (!text) return "";
        
        // Escape HTML
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Code block formatting
        escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        // Inline code formatting
        escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");

        // Bold formatting
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        // Paragraph line breaks
        return escaped.replace(/\n/g, "<br>");
    }

    // Scroll to the bottom of the chat history
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // Render a message in the UI
    function appendMessage(role, content, sources = []) {
        // Hide welcome screen if we have messages
        if (welcomeBox) {
            welcomeBox.style.display = "none";
        }

        const row = document.createElement("div");
        row.classList.add("message-row", role);

        const bubble = document.createElement("div");
        bubble.classList.add("message-bubble");
        
        if (role === "model") {
            bubble.innerHTML = formatMessage(content);
        } else {
            bubble.textContent = content;
        }

        row.appendChild(bubble);

        if (role === "model" && Array.isArray(sources) && sources.length) {
            const context = document.createElement("div");
            context.classList.add("retrieved-context");

            const title = document.createElement("strong");
            title.textContent = "Retrieved context";
            context.appendChild(title);

            const list = document.createElement("ul");
            sources.forEach(source => {
                const item = document.createElement("li");
                const score = Number(source.score);
                item.textContent = `${source.source || "Unknown source"}${Number.isFinite(score) ? ` (${score.toFixed(3)})` : ""}`;
                list.appendChild(item);
            });
            context.appendChild(list);
            row.appendChild(context);
        }

        chatHistory.appendChild(row);
        scrollToBottom();
    }

    // Render a typing indicator
    function showTypingIndicator() {
        const row = document.createElement("div");
        row.classList.add("message-row", "bot", "typing-indicator-row");

        const bubble = document.createElement("div");
        bubble.classList.add("message-bubble");

        const loader = document.createElement("div");
        loader.classList.add("typing-bubble");
        loader.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;

        bubble.appendChild(loader);
        row.appendChild(bubble);
        chatHistory.appendChild(row);
        scrollToBottom();
        return row;
    }

    // Load message history from DB
    async function loadHistory() {
        try {
            const response = await fetch(`/api/history/?session_id=${SESSION_ID}`);
            const data = await response.json();
            if (data.history && data.history.length > 0) {
                if (welcomeBox) welcomeBox.style.display = "none";
                data.history.forEach(msg => {
                    appendMessage(msg.role, msg.content);
                });
            }
        } catch (error) {
            console.error("Failed to load chat history:", error);
        }
    }

    // Submit new message to API
    async function sendMessage(text) {
        if (!text.trim() || sending) return;
        if (!apiKeyInput.value.trim()) {
            appendMessage("model", "Add your API key in Settings before chatting.");
            return;
        }

        // Append user message immediately
        appendMessage("user", text);
        messageInput.value = "";
        sending = true;
        updateSendState();

        // Show typing indicator
        const indicator = showTypingIndicator();

        try {
            const response = await fetch("/api/chat/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Provider": providerSelect.value,
                    "X-API-Key": apiKeyInput.value.trim(),
                    "X-Model": modelInput.value.trim()
                },
                body: JSON.stringify({
                    message: text,
                    session_id: SESSION_ID
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            indicator.remove();

            if (data.response) {
                appendMessage("model", data.response, data.sources);
            } else if (data.error) {
                appendMessage("model", `Error: ${data.error}`);
            }
        } catch (error) {
            indicator.remove();
            appendMessage("model", "Error: Failed to connect to server.");
            console.error(error);
        } finally {
            sending = false;
            updateSendState();
        }
    }

    // Form submit listener
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        sendMessage(messageInput.value);
    });

    // Clear history listener
    clearBtn.addEventListener("click", async () => {
        if (confirm("Are you sure you want to clear your conversation history?")) {
            try {
                const response = await fetch("/api/clear/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")
                    },
                    body: JSON.stringify({
                        session_id: SESSION_ID
                    })
                });

                if (response.ok) {
                    // Reset UI
                    const messages = chatHistory.querySelectorAll(".message-row");
                    messages.forEach(m => m.remove());
                    if (welcomeBox) {
                        welcomeBox.style.display = "block";
                    }
                }
            } catch (error) {
                console.error("Failed to clear history:", error);
            }
        }
    });

    // Suggestion chips listeners
    suggestionChips.forEach(chip => {
        chip.addEventListener("click", () => {
            sendMessage(chip.textContent.trim());
        });
    });

    // Initial history load
    updateSendState();
    loadHistory();
});
