document.addEventListener('DOMContentLoaded', () => {
    const rankConfig = getRankConfig();
    const prefix = rankConfig.prefix;

    const categorySelect = document.getElementById('trend-category');
    const subtitle = document.getElementById('trend-subtitle');
    const rangeButtons = document.querySelectorAll('.range-btn');
    const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;

    let categories = [];
    let trendRows = [];
    let latestData = null;
    let marketSummaryData = null;
    let selectedCategory = '';
    let selectedDays = 7;

    const els = {
        score: document.getElementById('trend-score'),
        scoreLabel: document.getElementById('trend-score-label'),
        diagnosis: document.getElementById('trend-diagnosis'),
        metricNew: document.getElementById('metric-new'),
        metricNewDaily: document.getElementById('metric-new-daily'),
        metricDropped: document.getElementById('metric-dropped'),
        metricDroppedDaily: document.getElementById('metric-dropped-daily'),
        metricActive: document.getElementById('metric-active'),
        metricRange: document.getElementById('metric-range'),
        marketSummary: document.getElementById('market-summary'),
        marketSource: document.getElementById('market-source'),
        hotGenres: document.getElementById('hot-genre-list'),
        hotTypes: document.getElementById('hot-type-list'),
        hotThemes: document.getElementById('hot-theme-list'),
        dailyBars: document.getElementById('daily-bars'),
        newBooks: document.getElementById('new-books-list'),
        risers: document.getElementById('risers-list'),
        reads: document.getElementById('reads-list'),
        summaries: document.getElementById('summary-feed'),
    };

    init();

    // 显示加载状态
    function showLoadingState() {
        const main = document.querySelector('.trend-shell main');
        if (main) {
            const loading = document.createElement('div');
            loading.className = 'loading-state';
            loading.id = 'trend-loading';
            loading.innerHTML = '<div class="loading-spinner"></div><span>正在加载趋势数据...</span>';
            main.insertBefore(loading, main.firstChild);
        }
    }
    showLoadingState();

    async function init() {
        try {
            const [dateIndex, latestIndex, latestAll, marketSummary] = await Promise.all([
                fetchJson(`data/dates_${prefix}.json?${cacheBuster}`).catch(() => null),
                fetchJson(`api/latest.json?${cacheBuster}`).catch(() => null),
                fetchJson(`api/latest/${prefix}_all.json?${cacheBuster}`)
                    .catch(() => fetchJson(`data/latest_${prefix}_ranks.json?${cacheBuster}`)),
                fetchJson(`data/market_summary_${prefix}.json?${cacheBuster}`).catch(() => null),
            ]);
            latestData = latestAll;
            marketSummaryData = marketSummary;

            categories = latestIndex && latestIndex.types
                ? latestIndex.types.filter(item => item.type !== 'all').map(item => item.type)
                : await loadCategoriesFallback();

            const dates = (dateIndex && dateIndex.dates || []).slice().sort();
            const trendDates = dates.slice(1);
            const trendFiles = await Promise.all(
                trendDates.map(date => fetchJson(`data/trends/${prefix}_${date}.json?${cacheBuster}`).catch(() => null))
            );
            trendRows = trendFiles
                .filter(Boolean)
                .map(item => ({ date: item.date, prevDate: item.prev_date, trends: item.trends || {} }))
                .sort((a, b) => a.date.localeCompare(b.date));

            if (trendRows.length === 0 || categories.length === 0) {
                renderEmpty('暂无可分析的趋势数据。');
                return;
            }

            // 移除加载状态
            const loadingEl = document.getElementById('trend-loading');
            if (loadingEl) loadingEl.remove();

            // 数据稀疏警告
            if (trendRows.length < 3) {
                const warn = document.createElement('div');
                warn.className = 'sparse-warning';
                warn.innerHTML = `<span class="warn-icon">⚠</span> 当前榜单仅有 ${trendRows.length} 天趋势数据，多日分析结果可能不够准确。数据积累中，请持续运行爬虫。`;
                const main = document.querySelector('.trend-shell main');
                if (main) main.insertBefore(warn, main.firstChild);
            }

            renderCategoryOptions();
            selectedCategory = getInitialCategory();
            categorySelect.value = selectedCategory;
            bindEvents();

            // 显示数据更新日期
            const dataDate = latestData?.date || '';
            if (dataDate) {
                subtitle.textContent = `数据更新于 ${dataDate}`;
            }
            render();
        } catch (err) {
            console.error(err);
            const loadingEl = document.getElementById('trend-loading');
            if (loadingEl) loadingEl.remove();
            renderEmpty('趋势数据加载失败，请稍后刷新重试。');
        }
    }

    async function loadCategoriesFallback() {
        const latest = await fetchJson(`data/latest_${prefix}_ranks.json?${cacheBuster}`);
        return (latest.categories || []).map(cat => cat.name);
    }

    function fetchJson(url) {
        return fetch(url).then(response => {
            if (!response.ok) throw new Error(`Failed to load ${url}`);
            return response.json();
        });
    }

    function bindEvents() {
        categorySelect.addEventListener('change', () => {
            selectedCategory = categorySelect.value;
            const url = new URL(window.location.href);
            url.searchParams.set('type', selectedCategory);
            history.replaceState(null, '', url);
            render();
        });

        rangeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                rangeButtons.forEach(item => item.classList.remove('active'));
                btn.classList.add('active');
                selectedDays = btn.dataset.days === 'all' ? 'all' : Number(btn.dataset.days);
                render();
            });
        });
    }

    function getInitialCategory() {
        const params = new URLSearchParams(window.location.search);
        const type = params.get('type');
        return categories.includes(type) ? type : categories[0];
    }

    function renderCategoryOptions() {
        categorySelect.innerHTML = categories.map(name =>
            `<option value="${escapeAttr(name)}">${escapeHtml(name)}</option>`
        ).join('');
    }

    function render() {
        const rows = getWindowRows()
            .map(row => ({
                date: row.date,
                prevDate: row.prevDate,
                trend: row.trends[selectedCategory] || null,
            }))
            .filter(row => row.trend);

        if (rows.length === 0) {
            renderEmpty(`${selectedCategory} 暂无趋势数据。`);
            return;
        }

        const totals = summarizeRows(rows);
        subtitle.textContent = `${selectedCategory} · ${rows[0].date} 至 ${rows[rows.length - 1].date} · ${rows.length} 个观察日`;

        renderOverview(rows, totals);
        renderMarketBoard(getWindowRows());
        renderDailyBars(rows);
        renderList(els.newBooks, collectNewBooks(rows));
        renderList(els.risers, collectRisers(rows));
        renderList(els.reads, collectReads(rows));
        renderSummaries(rows);
    }

    function getWindowRows() {
        if (selectedDays === 'all') return trendRows;
        return trendRows.slice(-selectedDays);
    }

    function summarizeRows(rows) {
        return rows.reduce((acc, row) => {
            const trend = row.trend;
            const riserCount = (trend.top_risers || []).length;
            const fallerCount = (trend.top_fallers || []).length;
            const readCount = (trend.reads_growth || []).length;
            acc.newCount += Number(trend.new_count || 0);
            acc.droppedCount += Number(trend.dropped_count || 0);
            acc.riserCount += riserCount;
            acc.fallerCount += fallerCount;
            acc.readCount += readCount;
            if ((trend.new_count || 0) || (trend.dropped_count || 0) || riserCount || fallerCount || readCount) {
                acc.activeDays += 1;
            }
            return acc;
        }, { newCount: 0, droppedCount: 0, riserCount: 0, fallerCount: 0, readCount: 0, activeDays: 0 });
    }

    function renderMarketBoard(rowsWindow) {
        const hotGenres = collectHotGenres(rowsWindow);
        const hotTypes = collectHotTypes(rowsWindow);
        const hotThemes = collectHotThemes(rowsWindow);

        if (!hotTypes.length && !hotGenres.length) {
            els.marketSummary.textContent = '暂无足够数据判断全站热点。';
            els.marketSource.textContent = '暂无数据';
            els.hotGenres.innerHTML = '<p class="muted-line">暂无数据。</p>';
            els.hotTypes.innerHTML = '<p class="muted-line">暂无数据。</p>';
            els.hotThemes.innerHTML = '<p class="muted-line">暂无数据。</p>';
            return;
        }

        const topGenres = hotGenres.slice(0, 2).map(item => item.name).join('、');
        const topTypes = hotTypes.slice(0, 3).map(item => item.name).join('、');
        const topThemes = hotThemes.slice(0, 6).map(item => item.name).join('、');
        const period = selectedDays === 'all' ? '全部样本' : `近 ${selectedDays} 日`;
        const fallbackSummary = `${period}里，${topGenres || topTypes} 是更热的分类，具体分类以 ${topTypes} 的榜单动能更强；题材上 ${topThemes} 反复出现，说明读者仍偏好强设定、强情绪钩子和明确爽点。`;
        const summaryData = getMarketSummaryForPeriod();
        els.marketSummary.textContent = summaryData ? summaryData.summary : fallbackSummary;
        els.marketSource.textContent = summaryData && summaryData.source === 'ai'
            ? `AI 总结 · ${summaryData.period || period}`
            : `规则兜底 · ${period}`;

        els.hotGenres.innerHTML = hotGenres.slice(0, 5).map((item, index) => `
            <button class="hot-type-row genre-row" type="button" data-type="${escapeAttr(item.leadCategory)}">
                <span>${index + 1}</span>
                <strong>${escapeHtml(item.name)}</strong>
                <small>${escapeHtml(item.categoryText)} · 新增 ${item.newCount} · 增长 ${item.readCount}</small>
                <em>${item.score}</em>
            </button>
        `).join('');

        els.hotTypes.innerHTML = hotTypes.slice(0, 6).map((item, index) => `
            <button class="hot-type-row" type="button" data-type="${escapeAttr(item.name)}">
                <span>${index + 1}</span>
                <strong>${escapeHtml(item.name)}</strong>
                <small>新增 ${item.newCount} · 增长 ${item.readCount}</small>
                <em>${item.score}</em>
            </button>
        `).join('');

        [els.hotGenres, els.hotTypes].forEach(container => {
            container.onclick = (e) => {
                const btn = e.target.closest('.hot-type-row');
                if (!btn) return;
                selectedCategory = btn.dataset.type;
                categorySelect.value = selectedCategory;
                const url = new URL(window.location.href);
                url.searchParams.set('type', selectedCategory);
                history.replaceState(null, '', url);
                render();
            };
        });

        els.hotThemes.innerHTML = hotThemes.slice(0, 14).map(item => `
            <span class="theme-chip" title="出现 ${item.count} 次，覆盖 ${item.categories.size} 个类型">
                ${escapeHtml(item.name)} <small>${item.count}</small>
            </span>
        `).join('');
    }

    function collectHotGenres(rowsWindow) {
        const hotTypes = collectHotTypes(rowsWindow);
        return hotTypes.filter(item => item.score > 0).map(item => ({
            ...item,
            leadCategory: item.name,
            categoryText: item.name,
        }));
    }

    function collectHotTypes(rowsWindow) {
        return categories.map(name => {
            const rows = rowsWindow
                .map(row => ({ trend: row.trends[name] || null }))
                .filter(row => row.trend);
            const totals = summarizeRows(rows);
            const score = Math.round(
                totals.newCount * 4 +
                totals.droppedCount * 2 +
                totals.riserCount * 2 +
                totals.readCount * 3 +
                totals.activeDays * 1.5
            );
            return {
                name,
                score,
                newCount: totals.newCount,
                droppedCount: totals.droppedCount,
                readCount: totals.readCount,
                activeDays: totals.activeDays,
            };
        })
            .filter(item => item.score > 0)
            .sort((a, b) => b.score - a.score);
    }

    function collectHotThemes(rowsWindow) {
        const keywords = [
            // 通用
            '重生', '穿越', '系统', '空间', '异能', '末世', '废土', '天灾', '囤货',
            '修仙', '玄学', '无限流', '悬疑', '直播', '综艺', '娱乐圈', '基建',
            // 女频
            '穿书', '快穿', '团宠', '萌宝', '幼崽', '女配', '炮灰',
            '反派', '权臣', '宅斗', '宫斗', '和离', '替嫁', '逃荒', '种田', '美食', '经商',
            '年代', '七零', '八零', '军婚', '豪门', '总裁', '真假千金', '先婚后爱', '追妻',
            '甜宠', '双洁', '强制爱', '无CP', '国运', '星际',
            '校园', '暗恋', '青梅竹马', '民国', '兽世', '远古',
            // 男频
            '赘婿', '逆袭', '战神', '龙王', '神医', '兵王', '都市', '高武', '修真',
            '玄幻', '仙侠', '剑道', '丹药', '炼器', '阵法', '升级', '打怪', '副本',
            '历史', '三国', '明朝', '架空', '争霸', '谋略', '谍战', '抗战',
            '科幻', '机甲', '赛博朋克', '游戏', '电竞', '体育',
            '动漫', '衍生', '同人',
        ];
        const scoreMap = new Map(keywords.map(name => [name, { name, count: 0, categories: new Set() }]));

        const latestCategories = latestData && latestData.categories ? latestData.categories : [];
        latestCategories.forEach(cat => {
            (cat.books || []).forEach((book, index) => {
                const weight = index < 10 ? 2 : 1;
                addThemeHits(scoreMap, keywords, `${book.title} ${book.intro || ''}`, cat.name, weight);
            });
        });

        rowsWindow.forEach(row => {
            categories.forEach(catName => {
                const trend = row.trends[catName];
                if (!trend) return;
                addThemeHits(scoreMap, keywords, (trend.new_books || []).join(' '), catName, 3);
                addThemeHits(scoreMap, keywords, trend.summary || '', catName, 1);
            });
        });

        return Array.from(scoreMap.values())
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count || b.categories.size - a.categories.size);
    }

    function addThemeHits(scoreMap, keywords, text, categoryName, weight) {
        const source = String(text || '');
        if (!source) return;
        keywords.forEach(keyword => {
            if (!source.includes(keyword)) return;
            const item = scoreMap.get(keyword);
            item.count += weight;
            item.categories.add(categoryName);
        });
    }

    function renderOverview(rows, totals) {
        const days = rows.length;
        const score = Math.round(
            (totals.newCount * 2 + totals.droppedCount * 1.5 + totals.riserCount + totals.readCount * 1.2) / Math.max(days, 1) * 10
        );
        const label = score >= 70 ? '强波动' : score >= 40 ? '有热度' : score >= 18 ? '稳态观察' : '低波动';

        els.score.textContent = String(score);
        els.scoreLabel.textContent = label;
        els.metricNew.textContent = totals.newCount;
        els.metricNewDaily.textContent = `日均 ${(totals.newCount / days).toFixed(1)} 本`;
        els.metricDropped.textContent = totals.droppedCount;
        els.metricDroppedDaily.textContent = `日均 ${(totals.droppedCount / days).toFixed(1)} 本`;
        els.metricActive.textContent = `${totals.activeDays}/${days}`;
        els.metricRange.textContent = selectedDays === 'all' ? '全部样本' : `近 ${selectedDays} 日`;

        const newVsDropped = totals.newCount >= totals.droppedCount ? '新入口多于掉榜，类型仍有补位空间' : '掉榜多于新增，榜单换血压力偏高';
        const readSignal = totals.readCount > days ? '阅读增长信号较密集' : '阅读增长信号相对集中';
        els.diagnosis.textContent = `${newVsDropped}；${readSignal}，可重点追踪连续上升和重复出现的题材关键词。`;
    }

    function renderDailyBars(rows) {
        const maxValue = Math.max(
            1,
            ...rows.map(row => Math.max(row.trend.new_count || 0, row.trend.dropped_count || 0))
        );

        els.dailyBars.innerHTML = rows.map(row => {
            const newCount = Number(row.trend.new_count || 0);
            const droppedCount = Number(row.trend.dropped_count || 0);
            const newHeight = Math.max(6, Math.round(newCount / maxValue * 88));
            const droppedHeight = Math.max(6, Math.round(droppedCount / maxValue * 88));
            return `
                <div class="daily-bar" title="${escapeAttr(row.date)} 新增 ${newCount} / 掉出 ${droppedCount}">
                    <div class="bar-stack">
                        <span class="bar-new" style="height:${newHeight}px"></span>
                        <span class="bar-dropped" style="height:${droppedHeight}px"></span>
                    </div>
                    <small>${row.date.slice(5)}</small>
                </div>
            `;
        }).join('');
    }

    function collectNewBooks(rows) {
        const items = [];
        rows.slice().reverse().forEach(row => {
            (row.trend.new_books || []).forEach(title => {
                items.push({ title, meta: row.date, value: '新上榜' });
            });
        });
        return items.slice(0, 12);
    }

    function collectRisers(rows) {
        const scoreMap = new Map();
        rows.forEach(row => {
            (row.trend.top_risers || []).forEach(item => {
                const current = scoreMap.get(item.title) || { title: item.title, score: 0, dates: [] };
                current.score += parseChange(item.change);
                current.dates.push(`${row.date} ${item.change}`);
                scoreMap.set(item.title, current);
            });
        });
        return Array.from(scoreMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, 10)
            .map(item => ({ title: item.title, meta: item.dates.slice(-2).join(' / '), value: item.score > 0 ? `+${item.score}` : `${item.score}` }));
    }

    function collectReads(rows) {
        const scoreMap = new Map();
        rows.forEach(row => {
            (row.trend.reads_growth || []).forEach(item => {
                const current = scoreMap.get(item.title) || { title: item.title, score: 0, dates: [] };
                current.score += parseReadsGrowth(item.growth);
                current.dates.push(`${row.date} ${item.growth}`);
                scoreMap.set(item.title, current);
            });
        });
        return Array.from(scoreMap.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, 10)
            .map(item => ({ title: item.title, meta: item.dates.slice(-2).join(' / '), value: formatReads(item.score) }));
    }

    function renderList(container, items) {
        if (!items.length) {
            container.innerHTML = '<p class="muted-line">暂无明显信号。</p>';
            return;
        }

        container.innerHTML = items.map(item => `
            <div class="compact-row">
                <div>
                    <strong>${escapeHtml(item.title)}</strong>
                    <small>${escapeHtml(item.meta)}</small>
                </div>
                <span>${escapeHtml(item.value)}</span>
            </div>
        `).join('');
    }

    function renderSummaries(rows) {
        const rowsWithSummary = rows
            .slice()
            .reverse()
            .filter(row => row.trend.summary)
            .slice(0, 10);

        if (!rowsWithSummary.length) {
            els.summaries.innerHTML = '<p class="muted-line">暂无摘要数据。</p>';
            return;
        }

        els.summaries.innerHTML = rowsWithSummary.map(row => `
            <article class="summary-item">
                <time>${escapeHtml(row.date)}</time>
                <div>${renderMarkdown(row.trend.summary)}</div>
            </article>
        `).join('');
    }

    function renderEmpty(message) {
        subtitle.textContent = message;
        els.score.textContent = '--';
        els.scoreLabel.textContent = '暂无数据';
        els.diagnosis.textContent = message;
        els.metricNew.textContent = '--';
        els.metricNewDaily.textContent = '--';
        els.metricDropped.textContent = '--';
        els.metricDroppedDaily.textContent = '--';
        els.metricActive.textContent = '--';
        els.metricRange.textContent = '--';
        els.marketSummary.textContent = message;
        els.marketSource.textContent = '暂无数据';
        els.hotGenres.innerHTML = '<p class="muted-line">暂无数据。</p>';
        els.hotTypes.innerHTML = '<p class="muted-line">暂无数据。</p>';
        els.hotThemes.innerHTML = '<p class="muted-line">暂无数据。</p>';
        els.dailyBars.innerHTML = `<div class="empty-state"><p>${escapeHtml(message)}</p></div>`;
        [els.newBooks, els.risers, els.reads, els.summaries].forEach(el => {
            el.innerHTML = '<p class="muted-line">暂无数据。</p>';
        });
    }

    function parseChange(value) {
        return Number(String(value || '0').replace('+', '')) || 0;
    }

    function getMarketSummaryForPeriod() {
        if (!marketSummaryData || !marketSummaryData.periods) return null;
        const key = selectedDays === 'all' ? 'all' : String(selectedDays);
        const item = marketSummaryData.periods[key];
        if (!item || !item.summary) return null;
        return item;
    }

    function parseReadsGrowth(value) {
        const raw = String(value || '0').replace('+', '').replace(/,/g, '').trim();
        const num = parseFloat(raw);
        if (Number.isNaN(num)) return 0;
        return raw.includes('万') ? num * 10000 : num;
    }

    function formatReads(value) {
        if (value >= 10000) return `+${(value / 10000).toFixed(1)}万`;
        return `+${Math.round(value)}`;
    }

    // renderMarkdown / escapeHtml / escapeAttr 已移至 js/utils.js
});
