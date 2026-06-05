/**
 * author.js — 创作灵感分析工具页面逻辑
 */

document.addEventListener('DOMContentLoaded', () => {
    const rankConfig = getRankConfig();
    const prefix = rankConfig.prefix;

    // 状态
    let themeTrends = null;
    let competitiveAnalysis = null;
    let readerProfile = null;
    let creationSuggestions = null;
    let latestRanks = null;
    let selectedPeriod = '7';
    let selectedCategory = '';
    let selectedGenre = '';
    let filteredGenres = [];
    let crossRef = {}; // 跨榜单索引: { genre: { suggestions: [{rankKey, label, periods}], profile: [{rankKey, label}] } }

    // 榜单名称映射
    const RANK_LABELS = {
        male_new: '男频新书榜', male_read: '男频阅读榜',
        female_new: '女频新书榜', female_read: '女频阅读榜'
    };

    // 原始分类列表（从数据中动态获取）
    let allCategoryNames = [];

    const CACHE_BUST = `v=${Math.floor(Date.now() / 600000)}`;

    // escapeHtml / escapeAttr / renderMarkdown 已移至 js/utils.js

    async function fetchJson(url) {
        try {
            const resp = await fetch(`${url}?${CACHE_BUST}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (e) {
            console.warn(`Failed to load ${url}:`, e);
            return null;
        }
    }

    // parseReads 已移至 js/utils.js

    // ========== 数据加载 ==========
    async function loadData() {
        const [themes, competitive, profile, suggestions, ranks] = await Promise.all([
            fetchJson(`data/author/theme_trends_${prefix}.json`),
            fetchJson(`data/author/competitive_analysis_${prefix}.json`),
            fetchJson(`data/author/reader_profile_${prefix}.json`),
            fetchJson(`data/author/creation_suggestions_${prefix}.json`),
            fetchJson(`data/latest_${prefix}_ranks.json`),
        ]);

        themeTrends = themes;
        competitiveAnalysis = competitive;
        readerProfile = profile;
        creationSuggestions = suggestions;
        latestRanks = ranks;

        // 从数据中提取原始分类列表
        const profileKeys = Object.keys(profile?.genre_profiles || {});
        const rankCats = (ranks?.categories || []).map(c => c.name).filter(Boolean);
        allCategoryNames = profileKeys.length > 0 ? profileKeys : rankCats;
        filteredGenres = allCategoryNames; // 兼容旧引用

        // 设置全局数据（供 export.js 使用）
        window.authorData = {
            themeTrends,
            competitiveAnalysis,
            readerProfile,
            creationSuggestions,
            latestRanks,
        };

        // 更新副标题
        const date = themeTrends?.date || competitiveAnalysis?.date || '';
        if (date) {
            document.getElementById('author-subtitle').textContent = `数据更新于 ${date}`;
        }

        // 数据稀疏警告
        const periods = themeTrends?.periods || {};
        const allPeriodDays = Object.values(periods).reduce((sum, p) => {
            return sum + (p.themes?.length || 0);
        }, 0);
        if (allPeriodDays === 0) {
            const warn = document.createElement('div');
            warn.className = 'sparse-warning';
            warn.innerHTML = `<span class="warn-icon">⚠</span> 当前榜单的题材分析数据不足，部分功能可能显示为空。数据积累中，请持续运行爬虫以获取更完整的分析。`;
            const main = document.querySelector('.author-shell main');
            if (main) main.insertBefore(warn, main.firstChild);
        }

        // 异步加载跨榜单索引（不阻塞主渲染）
        buildCrossRef();

        // 初始化 UI
        initControls();
        render();
    }

    // 构建跨榜单数据索引
    async function buildCrossRef() {
        const otherRanks = Object.keys(RANK_LABELS).filter(k => k !== prefix);
        const ref = {};

        // 并行加载其他榜单的创作建议和读者画像
        const results = await Promise.all(otherRanks.map(async rankKey => {
            const [sugg, prof] = await Promise.all([
                fetchJson(`data/author/creation_suggestions_${rankKey}.json`),
                fetchJson(`data/author/reader_profile_${rankKey}.json`),
            ]);
            return { rankKey, sugg, prof };
        }));

        for (const { rankKey, sugg, prof } of results) {
            const label = RANK_LABELS[rankKey];
            // 创作建议：收集有数据的分类和周期
            if (sugg?.periods) {
                for (const [period, pdata] of Object.entries(sugg.periods)) {
                    for (const genre of Object.keys(pdata.genre_suggestions || {})) {
                        if (!ref[genre]) ref[genre] = { suggestions: {}, profile: [] };
                        if (!ref[genre].suggestions[rankKey]) {
                            ref[genre].suggestions[rankKey] = { label, periods: [] };
                        }
                        ref[genre].suggestions[rankKey].periods.push(period);
                    }
                }
            }
            // 读者画像：收集有数据的分类
            if (prof?.genre_profiles) {
                for (const genre of Object.keys(prof.genre_profiles)) {
                    if (!ref[genre]) ref[genre] = { suggestions: {}, profile: [] };
                    if (!ref[genre].profile.some(p => p.rankKey === rankKey)) {
                        ref[genre].profile.push({ rankKey, label });
                    }
                }
            }
        }

        crossRef = ref;
    }

    // ========== 控件初始化 ==========
    function initControls() {
        // 周期选择器
        document.querySelectorAll('#author-period .range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#author-period .range-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedPeriod = btn.dataset.days;
                renderThemeSection();
                renderSuggestSection();
            });
        });

        // 竞品分类选择器
        const competeSelect = document.getElementById('compete-category');
        if (competitiveAnalysis?.categories) {
            const categories = Object.keys(competitiveAnalysis.categories);
            selectedCategory = categories[0] || '';
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                competeSelect.appendChild(opt);
            });
            competeSelect.addEventListener('change', () => {
                selectedCategory = competeSelect.value;
                renderCompeteSection();
            });
        }

        // 分类选择器（创作建议）— 从数据中动态获取
        const suggestSelect = document.getElementById('suggest-genre');
        allCategoryNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            suggestSelect.appendChild(opt);
        });
        selectedGenre = allCategoryNames[0] || '';
        suggestSelect.addEventListener('change', () => {
            selectedGenre = suggestSelect.value;
            renderSuggestSection();
        });

        // 分类选择器（读者画像）
        const profileSelect = document.getElementById('profile-genre');
        allCategoryNames.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            profileSelect.appendChild(opt);
        });
        profileSelect.addEventListener('change', () => {
            renderProfileSection(profileSelect.value);
        });
    }

    // ========== 渲染总入口 ==========
    function render() {
        renderThemeSection();
        renderCompeteSection();
        renderSuggestSection();
        renderProfileSection(allCategoryNames[0] || '');
    }

    // ========== Section 1: 题材热度 ==========
    function renderThemeSection() {
        const periodData = themeTrends?.periods?.[selectedPeriod];
        if (!periodData) {
            document.getElementById('theme-cloud').innerHTML = '<p class="error-hint">暂无题材数据</p>';
            return;
        }

        const themes = periodData.themes || [];
        const combos = periodData.top_combinations || [];

        // 渲染题材云
        renderThemeCloud(themes);

        // 渲染趋势图
        renderThemeTrendChart(themes);

        // 渲染共现卡片
        renderComboCards(combos);
    }

    function renderThemeCloud(themes) {
        const container = document.getElementById('theme-cloud');
        const maxCount = Math.max(1, ...themes.slice(0, 20).map(t => t.total_count));

        container.innerHTML = themes.slice(0, 20).map(item => {
            const intensity = Math.min(1, item.total_count / maxCount);
            const bgColor = `rgba(240, 79, 56, ${0.04 + intensity * 0.15})`;
            const borderColor = `rgba(240, 79, 56, ${0.1 + intensity * 0.25})`;

            let arrow = '';
            if (item.trend_direction === 'rising') {
                arrow = '<span class="trend-arrow up"> UP</span>';
            } else if (item.trend_direction === 'falling') {
                arrow = '<span class="trend-arrow down"> DN</span>';
            }

            return `<span class="theme-chip" style="background:${bgColor};border-color:${borderColor}">
                ${escapeHtml(item.name)}${arrow} <small>${item.total_count}</small>
            </span>`;
        }).join('');
    }

    function renderThemeTrendChart(themes) {
        const container = document.getElementById('theme-trend-chart');
        const top6 = themes.filter(t => t.daily_counts && t.daily_counts.length > 0).slice(0, 6);

        if (top6.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无趋势数据</p>';
            return;
        }

        const maxVal = Math.max(1, ...top6.flatMap(t => t.daily_counts.map(d => d.count)));
        const width = 480, height = 200, padY = 20, padX = 50;
        const plotW = width - padX * 2, plotH = height - padY * 2;

        const colors = ['#f04f38', '#0ea5e9', '#10b981', '#f59e0b', '#7c3aed', '#64748b'];

        const lines = top6.map((theme, i) => {
            const points = theme.daily_counts.map((d, j) => {
                const x = padX + (j / Math.max(1, theme.daily_counts.length - 1)) * plotW;
                const y = padY + plotH - (d.count / maxVal) * plotH;
                return `${x},${y}`;
            }).join(' ');
            return `<polyline points="${points}" fill="none" stroke="${colors[i]}" stroke-width="2" stroke-linecap="round"/>`;
        }).join('');

        const legend = top6.map((t, i) =>
            `<span style="color:${colors[i]}">● ${escapeHtml(t.name)}</span>`
        ).join(' ');

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto">${lines}</svg>
            <div class="chart-legend">${legend}</div>
        `;
    }

    function renderComboCards(combos) {
        const container = document.getElementById('combo-cards');
        container.innerHTML = combos.slice(0, 5).map(c => `
            <div class="combo-card">
                <div class="combo-keywords">
                    <span class="combo-kw">${escapeHtml(c.themes[0])}</span>
                    <span class="combo-bridge">+</span>
                    <span class="combo-kw">${escapeHtml(c.themes[1])}</span>
                </div>
                <div class="combo-meta">共现 ${c.co_count} 次 · ${(c.categories || []).slice(0, 3).join('、')}</div>
            </div>
        `).join('');
    }

    // ========== Section 2: 竞品对标 ==========
    function renderCompeteSection() {
        const catData = competitiveAnalysis?.categories?.[selectedCategory];
        if (!catData) {
            document.getElementById('compete-keywords').innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        // 共性关键词
        renderPresenceBars('compete-keywords', catData.shared_keywords || []);

        // 标题模式
        renderTitlePatterns('compete-titles', catData.title_patterns || {});

        // 阅读量分布
        renderReadsChart('compete-reads', catData.top10_books || []);

        // 简介钩子
        renderHookAnalysis('compete-hooks', catData.intro_patterns || {});
    }

    function renderPresenceBars(containerId, keywords) {
        const container = document.getElementById(containerId);
        const filtered = keywords.filter(k => k.presence >= 0.2);

        if (filtered.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无共性关键词</p>';
            return;
        }

        container.innerHTML = filtered.map(k => `
            <div class="presence-row">
                <span class="presence-label">${escapeHtml(k.keyword)}</span>
                <div class="presence-bar-track">
                    <div class="presence-bar-fill" style="width:${k.presence * 100}%"></div>
                </div>
                <span class="presence-value">${Math.round(k.presence * 100)}%</span>
            </div>
        `).join('');
    }

    function renderTitlePatterns(containerId, patterns) {
        const container = document.getElementById(containerId);
        const structures = patterns.common_structures || [];

        container.innerHTML = `
            <div class="pattern-stats">
                <div class="pattern-stat">
                    <span>平均字数</span>
                    <strong>${(patterns.avg_length || 0).toFixed(1)}</strong>
                </div>
                <div class="pattern-stat">
                    <span>含标点比例</span>
                    <strong>${Math.round((patterns.has_punctuation || 0) * 100)}%</strong>
                </div>
            </div>
            <div class="pattern-structures">
                ${structures.map(s => `<span class="theme-chip">${escapeHtml(s)}</span>`).join('') || '<span class="error-hint">暂无常见结构</span>'}
            </div>
        `;
    }

    function renderReadsChart(containerId, books) {
        const container = document.getElementById(containerId);
        if (books.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        const maxReads = Math.max(...books.map(b => parseReads(b.reads)));

        container.innerHTML = books.map((b, i) => {
            const reads = parseReads(b.reads);
            const pct = maxReads > 0 ? (reads / maxReads * 100) : 0;
            return `<div class="reads-bar-row">
                <span class="reads-rank">#${i + 1}</span>
                <div class="reads-bar-track">
                    <div class="reads-bar-fill" style="width:${pct}%"></div>
                </div>
                <span class="reads-value">${escapeHtml(b.reads)}</span>
            </div>`;
        }).join('');
    }

    function renderHookAnalysis(containerId, patterns) {
        const container = document.getElementById(containerId);
        const hooks = patterns.common_hooks || [];
        const settings = patterns.common_settings || [];

        let html = '';

        if (hooks.length > 0) {
            html += '<div style="margin-bottom:12px"><small style="color:var(--text-muted);font-size:12px">常见钩子</small></div>';
            html += '<div class="hook-analysis">';
            html += hooks.map(h => `<span class="hook-chip">${escapeHtml(h)}</span>`).join('');
            html += '</div>';
        }

        if (settings.length > 0) {
            html += '<div style="margin-top:16px;margin-bottom:12px"><small style="color:var(--text-muted);font-size:12px">常见设定</small></div>';
            html += '<div class="hook-analysis">';
            html += settings.map(s => `<span class="hook-chip" style="background:rgba(16,185,129,0.08);border-color:rgba(16,185,129,0.2);color:var(--green)">${escapeHtml(s)}</span>`).join('');
            html += '</div>';
        }

        if (!html) {
            html = '<p class="error-hint">暂无钩子分析</p>';
        }

        container.innerHTML = html;
    }

    // ========== 周期切换辅助 ==========
    const PERIOD_LABELS = { '7': '7天', '14': '14天', '30': '30天', 'all': '全量' };

    function switchPeriod(days) {
        selectedPeriod = days;
        document.querySelectorAll('#author-period .range-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.days === days);
        });
        renderThemeSection();
        renderSuggestSection();
    }

    // 生成跨榜单链接 HTML
    function buildCrossRankLinks(genre, type) {
        const entry = crossRef[genre];
        if (!entry) return '';
        if (type === 'suggestions' && Object.keys(entry.suggestions).length > 0) {
            return Object.entries(entry.suggestions).map(([rankKey, info]) => {
                const periodText = info.periods.map(p => PERIOD_LABELS[p] || `${p}天`).join('、');
                return `<a class="cross-rank-link" href="author.html?rank=${rankKey}">${escapeHtml(info.label)} · ${periodText}</a>`;
            }).join(' ');
        }
        if (type === 'profile' && entry.profile.length > 0) {
            return entry.profile.map(({ rankKey, label }) =>
                `<a class="cross-rank-link" href="author.html?rank=${rankKey}">${escapeHtml(label)}</a>`
            ).join(' ');
        }
        return '';
    }

    // 收集各周期有数据的分类数量
    function getPeriodSummary() {
        if (!creationSuggestions?.periods) return {};
        const summary = {};
        for (const [k, v] of Object.entries(creationSuggestions.periods)) {
            const count = Object.keys(v.genre_suggestions || {}).length;
            if (count > 0) summary[k] = count;
        }
        return summary;
    }

    // ========== Section 3: 创作建议 ==========
    function renderSuggestSection() {
        const panel = document.getElementById('suggest-panel');
        const crossContainer = document.getElementById('suggest-cross');

        // 查找当前周期的建议数据
        const periodKey = selectedPeriod === 'all' ? 'all' : selectedPeriod;
        const periodData = creationSuggestions?.periods?.[periodKey];

        if (!periodData) {
            const periodSummary = getPeriodSummary();
            const availableKeys = Object.keys(periodSummary);
            if (availableKeys.length > 0) {
                const btns = availableKeys.map(k =>
                    `<button class="period-hint-btn" data-period="${k}">${PERIOD_LABELS[k] || k}天（${periodSummary[k]}个分类）</button>`
                ).join(' ');
                panel.innerHTML = `<p class="error-hint">当前周期暂无创作建议数据（由 AI 生成）。以下周期有数据，点击切换：${btns}</p>`;
            } else {
                panel.innerHTML = '<p class="error-hint">暂无创作建议数据。此功能需要配置 AI 服务后运行 <code>python scripts/build_latest.py</code> 生成。</p>';
            }
            crossContainer.innerHTML = '';
            // 绑定快捷切换按钮
            panel.querySelectorAll('.period-hint-btn').forEach(btn => {
                btn.addEventListener('click', () => switchPeriod(btn.dataset.period));
            });
            return;
        }

        const availableGenres = Object.keys(periodData.genre_suggestions || {});
        const suggestion = periodData.genre_suggestions?.[selectedGenre];
        if (!suggestion) {
            const parts = [];
            // 同榜其他分类
            if (availableGenres.length > 0) {
                const genreLinks = availableGenres.map(g =>
                    `<button class="genre-hint-btn" data-genre="${escapeAttr(g)}">${escapeHtml(g)}</button>`
                ).join(' ');
                parts.push(`本榜以下分类有数据：${genreLinks}`);
            }
            // 跨榜单链接
            const crossLinks = buildCrossRankLinks(selectedGenre, 'suggestions');
            if (crossLinks) {
                parts.push(`其他榜单有数据：${crossLinks}`);
            }
            if (parts.length > 0) {
                panel.innerHTML = `<p class="error-hint">「${escapeHtml(selectedGenre)}」暂无创作建议。${parts.join('')}</p>`;
            } else {
                panel.innerHTML = '<p class="error-hint">当前周期暂无任何分类的创作建议</p>';
            }
            // 绑定同榜切换按钮
            panel.querySelectorAll('.genre-hint-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    selectedGenre = btn.dataset.genre;
                    document.getElementById('suggest-genre').value = selectedGenre;
                    renderSuggestSection();
                });
            });
        } else {
            panel.innerHTML = renderSuggestionContent(suggestion);
            panel.querySelectorAll('.book-copy-btn[data-copy-text]').forEach(btn => {
                btn.addEventListener('click', () => {
                    navigator.clipboard.writeText(btn.dataset.copyText).then(() => {
                        if (typeof showToast === 'function') showToast('已复制');
                        btn.textContent = '已复制';
                        setTimeout(() => { btn.textContent = '复制'; }, 1500);
                    }).catch(() => {
                        // Fallback: 使用传统方式复制
                        const ta = document.createElement('textarea');
                        ta.value = btn.dataset.copyText;
                        ta.style.position = 'fixed';
                        ta.style.opacity = '0';
                        document.body.appendChild(ta);
                        ta.select();
                        document.execCommand('copy');
                        document.body.removeChild(ta);
                        if (typeof showToast === 'function') showToast('已复制');
                        btn.textContent = '已复制';
                        setTimeout(() => { btn.textContent = '复制'; }, 1500);
                    });
                });
            });
        }

        // 跨分类机会
        const crossOpps = periodData.cross_genre_opportunities || [];
        if (crossOpps.length > 0) {
            crossContainer.innerHTML = crossOpps.map(opp => `
                <div class="cross-card">
                    <div class="cross-combo">${escapeHtml(opp.combination)}</div>
                    <p class="cross-reason">${renderMarkdown(opp.reasoning)}</p>
                    <div class="cross-hook">示例钩子: ${escapeHtml(opp.example_hook)}</div>
                </div>
            `).join('');
        } else {
            crossContainer.innerHTML = '<p class="error-hint">暂无跨分类机会数据</p>';
        }
    }

    function renderSuggestionContent(suggestion) {
        let html = '';

        // 市场格局
        if (suggestion.market_position) {
            html += `<div class="suggest-section">
                <h3>市场格局</h3>
                <p>${renderMarkdown(suggestion.market_position)}</p>
            </div>`;
        }

        // 推荐题材
        if (suggestion.recommended_themes?.length > 0) {
            html += `<div class="suggest-section">
                <h3>推荐题材</h3>
                <div class="suggest-chips">
                    ${suggestion.recommended_themes.map(t =>
                        `<span class="theme-chip recommend">${escapeHtml(t)}</span>`
                    ).join('')}
                </div>
            </div>`;
        }

        // 差异化机会
        if (suggestion.gap_opportunities?.length > 0) {
            html += `<div class="suggest-section">
                <h3>差异化机会</h3>
                ${suggestion.gap_opportunities.map(g =>
                    `<div class="gap-card">${renderMarkdown(g)}</div>`
                ).join('')}
            </div>`;
        }

        // 书名参考
        if (suggestion.title_suggestions?.length > 0) {
            html += `<div class="suggest-section">
                <h3>书名参考</h3>
                ${suggestion.title_suggestions.map(t =>
                    `<div class="title-suggestion-card">
                        <span>${escapeHtml(t)}</span>
                        <button class="book-copy-btn" data-copy-text="${escapeAttr(t)}">复制</button>
                    </div>`
                ).join('')}
            </div>`;
        }

        // 饱和题材
        if (suggestion.avoid_themes?.length > 0) {
            html += `<div class="suggest-section">
                <h3>饱和题材（建议避坑）</h3>
                <div class="suggest-chips">
                    ${suggestion.avoid_themes.map(t =>
                        `<span class="theme-chip avoid">${escapeHtml(t)}</span>`
                    ).join('')}
                </div>
            </div>`;
        }

        // 综合建议
        if (suggestion.summary) {
            html += `<div class="suggest-section">
                <h3>综合建议</h3>
                <div class="suggest-summary">
                    <p>${renderMarkdown(suggestion.summary)}</p>
                </div>
            </div>`;
        }

        return html || '<p class="error-hint">暂无建议内容</p>';
    }

    // ========== Section 4: 读者画像 ==========
    function renderProfileSection(genreName) {
        const profile = readerProfile?.genre_profiles?.[genreName];
        if (!profile) {
            const allGenres = Object.keys(readerProfile?.genre_profiles || {});
            const parts = [];
            if (allGenres.length > 0) {
                parts.push(`本榜以下分类有数据：${allGenres.map(g =>
                    `<button class="genre-hint-btn" data-genre="${escapeAttr(g)}">${escapeHtml(g)}</button>`
                ).join(' ')}`);
            }
            const crossLinks = buildCrossRankLinks(genreName, 'profile');
            if (crossLinks) {
                parts.push(`其他榜单有数据：${crossLinks}`);
            }
            const hint = parts.length > 0
                ? `暂无「${escapeHtml(genreName)}」的画像数据。${parts.join('')}`
                : '暂无画像数据。此功能需要配置 AI 服务后运行数据生成。';
            ['profile-elements', 'profile-emotion', 'profile-golden', 'profile-setting'].forEach(id => {
                const el = document.getElementById(id);
                el.innerHTML = `<p class="error-hint">${hint}</p>`;
                el.querySelectorAll('.genre-hint-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        document.getElementById('profile-genre').value = btn.dataset.genre;
                        renderProfileSection(btn.dataset.genre);
                    });
                });
            });
            return;
        }

        // 热门元素
        renderElementBars('profile-elements', profile.top_elements || []);

        // 情感偏好
        renderEmotionDonut('profile-emotion', profile.emotional_preference || {});

        // 金手指偏好
        renderGoldenFingers('profile-golden', profile.golden_finger_preference || []);

        // 背景设定
        renderSettingBars('profile-setting', profile.setting_preference || {});
    }

    function renderElementBars(containerId, elements) {
        const container = document.getElementById(containerId);
        if (elements.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        const maxWeight = Math.max(1, ...elements.map(e => e.weight));

        container.innerHTML = elements.slice(0, 10).map(e => `
            <div class="presence-row">
                <span class="presence-label">${escapeHtml(e.keyword)}</span>
                <div class="presence-bar-track">
                    <div class="presence-bar-fill" style="width:${e.weight / maxWeight * 100}%"></div>
                </div>
                <span class="presence-value">${e.weight}</span>
            </div>
        `).join('');
    }

    function renderEmotionDonut(containerId, emotions) {
        const container = document.getElementById(containerId);
        const total = (emotions.sweet || 0) + (emotions.angst || 0) +
                      (emotions.power_fantasy || 0) + (emotions.daily_life || 0);

        if (total === 0) {
            container.innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        const sweetDeg = (emotions.sweet / total * 360);
        const angstDeg = sweetDeg + (emotions.angst / total * 360);
        const powerDeg = angstDeg + (emotions.power_fantasy / total * 360);

        container.innerHTML = `
            <div class="donut-wrapper">
                <div class="donut-chart" style="background:conic-gradient(
                    var(--accent) 0deg ${sweetDeg}deg,
                    var(--info) ${sweetDeg}deg ${angstDeg}deg,
                    var(--green) ${angstDeg}deg ${powerDeg}deg,
                    var(--amber) ${powerDeg}deg 360deg
                )"></div>
                <div class="donut-legend">
                    <div><span style="color:var(--accent)">●</span> 甜宠 ${Math.round(emotions.sweet / total * 100)}%</div>
                    <div><span style="color:var(--info)">●</span> 虐恋 ${Math.round(emotions.angst / total * 100)}%</div>
                    <div><span style="color:var(--green)">●</span> 爽文 ${Math.round(emotions.power_fantasy / total * 100)}%</div>
                    <div><span style="color:var(--amber)">●</span> 日常 ${Math.round(emotions.daily_life / total * 100)}%</div>
                </div>
            </div>
        `;
    }

    function renderGoldenFingers(containerId, fingers) {
        const container = document.getElementById(containerId);
        if (fingers.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        container.innerHTML = fingers.slice(0, 8).map((f, i) => `
            <div class="golden-row">
                <span class="golden-rank">${i + 1}</span>
                <span class="golden-name">${escapeHtml(f.type)}</span>
                <div class="presence-bar-track">
                    <div class="presence-bar-fill" style="width:${f.frequency * 100}%"></div>
                </div>
                <span class="presence-value">${Math.round(f.frequency * 100)}%</span>
            </div>
        `).join('');
    }

    function renderSettingBars(containerId, settings) {
        const container = document.getElementById(containerId);
        const entries = Object.entries(settings);

        if (entries.length === 0) {
            container.innerHTML = '<p class="error-hint">暂无数据</p>';
            return;
        }

        const maxValue = Math.max(1, ...entries.map(([, v]) => v));

        container.innerHTML = entries.map(([setting, value]) => `
            <div class="presence-row">
                <span class="presence-label">${escapeHtml(setting)}</span>
                <div class="presence-bar-track">
                    <div class="presence-bar-fill" style="width:${value / maxValue * 100}%"></div>
                </div>
                <span class="presence-value">${Math.round(value * 100)}%</span>
            </div>
        `).join('');
    }

    // ========== 初始化 ==========
    // 显示加载状态
    function showLoadingState() {
        const sections = document.querySelectorAll('.author-section');
        sections.forEach(section => {
            const content = section.querySelector('.theme-grid, .compete-grid, .profile-grid, .suggest-panel, .combo-cards, .cross-cards');
            if (content && !content.children.length) {
                content.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><span>正在加载数据...</span></div>';
            }
        });
    }
    showLoadingState();
    loadData();
});
