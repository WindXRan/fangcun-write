/* ============================================================
   顶部导航栏组件 + API配置弹窗
   在所有页面注入统一的导航栏
   ============================================================ */

(function () {
    const currentRank = getRankTypeFromURL();
    const currentConfig = getRankConfig();

    // 确定当前页面类型
    const page = location.pathname.split("/").pop() || "index.html";
    const isIndex = page === "index.html" || page === "" || page === "/";
    const isTrend = page === "trend.html";
    const isAuthor = page === "author.html";

    function getPageBase() {
        if (isTrend) return "trend.html";
        if (isAuthor) return "author.html";
        return "index.html";
    }

    // 构建导航栏HTML
    function buildNavHTML() {
        const tabs = Object.entries(RANK_TYPES).map(([key, val]) => {
            const active = key === currentRank ? " active" : "";
            const href = buildPageURL(key).replace(page, getPageBase());
            return `<a class="nav-tab${active}" href="${href}">${val.name}</a>`;
        }).join("");

        const extraLinks = [];
        if (!isTrend) extraLinks.push(`<a class="nav-extra-link" href="trend.html?rank=${currentRank}">趋势</a>`);
        if (!isAuthor) extraLinks.push(`<a class="nav-extra-link" href="author.html?rank=${currentRank}">灵感</a>`);
        if (isTrend || isAuthor) extraLinks.push(`<a class="nav-extra-link" href="index.html?rank=${currentRank}">榜单</a>`);
        extraLinks.push(`<a class="nav-extra-link" href="library.html">📚 书库</a>`);

        return `
        <div class="top-nav-inner">
            <div class="nav-brand">
                <span class="nav-brand-icon">T</span>
                <span class="nav-brand-text">番茄指数</span>
            </div>
            <div class="nav-tabs">${tabs}</div>
            <div class="nav-right">
                ${extraLinks.join("")}
                <button class="nav-settings-btn" id="nav-settings-btn" title="API 配置" aria-label="设置">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                </button>
            </div>
        </div>`;
    }

    // 构建API配置弹窗HTML
    function buildModalHTML() {
        return `
        <div class="api-modal-overlay" id="api-modal-overlay">
            <div class="api-modal">
                <div class="api-modal-header">
                    <h3>API 配置</h3>
                    <button class="api-modal-close" id="api-modal-close">&times;</button>
                </div>
                <div class="api-modal-body">
                    <p class="api-modal-desc">配置 OpenAI 兼容的 API 接口，用于 AI 趋势分析。配置保存在本地浏览器中。</p>
                    <div class="api-field">
                        <label for="api-base-url">API Base URL</label>
                        <input type="text" id="api-base-url" placeholder="https://api.example.com/v1">
                    </div>
                    <div class="api-field">
                        <label for="api-key">API Key</label>
                        <input type="password" id="api-key" placeholder="sk-...">
                    </div>
                    <div class="api-field">
                        <label for="api-model">Model</label>
                        <input type="text" id="api-model" placeholder="gpt-4o-mini">
                    </div>
                </div>
                <div class="api-modal-footer">
                    <button class="api-btn api-btn-clear" id="api-btn-clear">清除</button>
                    <button class="api-btn api-btn-save" id="api-btn-save">保存</button>
                </div>
            </div>
        </div>`;
    }

    // 渲染导航栏
    function renderNav() {
        const navEl = document.getElementById("top-nav");
        if (!navEl) return;
        navEl.innerHTML = buildNavHTML();

        // 插入弹窗到body
        document.body.insertAdjacentHTML("beforeend", buildModalHTML());

        // 绑定事件
        bindModalEvents();
    }

    // API配置 localStorage 读写
    function loadApiConfig() {
        try {
            const raw = localStorage.getItem("fanqie_api_config");
            return raw ? JSON.parse(raw) : { baseUrl: "", apiKey: "", model: "" };
        } catch {
            return { baseUrl: "", apiKey: "", model: "" };
        }
    }

    function saveApiConfig(config) {
        localStorage.setItem("fanqie_api_config", JSON.stringify(config));
    }

    function bindModalEvents() {
        const overlay = document.getElementById("api-modal-overlay");
        const settingsBtn = document.getElementById("nav-settings-btn");
        const closeBtn = document.getElementById("api-modal-close");
        const saveBtn = document.getElementById("api-btn-save");
        const clearBtn = document.getElementById("api-btn-clear");

        if (!settingsBtn || !overlay) return;

        function openModal() {
            const cfg = loadApiConfig();
            document.getElementById("api-base-url").value = cfg.baseUrl || "";
            document.getElementById("api-key").value = cfg.apiKey || "";
            document.getElementById("api-model").value = cfg.model || "";
            overlay.classList.add("open");
        }

        function closeModal() {
            overlay.classList.remove("open");
        }

        settingsBtn.addEventListener("click", openModal);
        closeBtn.addEventListener("click", closeModal);
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) closeModal();
        });

        saveBtn.addEventListener("click", () => {
            saveApiConfig({
                baseUrl: document.getElementById("api-base-url").value.trim(),
                apiKey: document.getElementById("api-key").value.trim(),
                model: document.getElementById("api-model").value.trim(),
            });
            closeModal();
        });

        clearBtn.addEventListener("click", () => {
            document.getElementById("api-base-url").value = "";
            document.getElementById("api-key").value = "";
            document.getElementById("api-model").value = "";
            localStorage.removeItem("fanqie_api_config");
        });
    }

    // 动态更新页面标题
    function updatePageTitle() {
        document.title = `番茄${currentConfig.name} · 番茄指数`;
        const subtitle = document.querySelector(".sidebar-subtitle");
        if (subtitle) subtitle.textContent = `${currentConfig.gender}${currentConfig.name.replace(/^(男频|女频)/, "")}追踪`;
    }

    // DOM Ready后执行
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => { renderNav(); updatePageTitle(); });
    } else {
        renderNav();
        updatePageTitle();
    }
})();
