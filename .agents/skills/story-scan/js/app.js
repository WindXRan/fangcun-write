document.addEventListener('DOMContentLoaded', () => {
    const rankConfig = getRankConfig();
    const prefix = rankConfig.prefix;

    const categoryList = document.getElementById('category-list');
    const waterfall = document.getElementById('books-waterfall');
    const updateDate = document.getElementById('update-date');
    const categoryTitle = document.getElementById('current-category-title');
    const trendStats = document.getElementById('trend-stats');
    const aiContent = document.getElementById('ai-content');
    const trendPanel = document.getElementById('trend-panel');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const dateDisplay = document.getElementById('date-display');
    const datePickerBtn = document.getElementById('date-picker-btn');
    const dateInput = document.getElementById('date-input');
    const datePrevBtn = document.getElementById('date-prev');
    const dateNextBtn = document.getElementById('date-next');

    let allData = null;
    let availableDates = [];   // sorted list of "YYYY-MM-DD"
    let currentDateIndex = -1; // index into availableDates
    let currentCategory = null; // preserve selected category across date switches

    // Cache-busting: 每10分钟一个新key，避免浏览器缓存旧JSON
    const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;

    // ========== Copy Toast ==========
    // showToast 由 export.js 提供全局版本

    function copyBookInfo(e, book) {
        e.preventDefault();
        e.stopPropagation();
        const text = `${book.title}\n作者：${book.author}\n阅读量：${book.reads}\n简介：${book.intro || '无'}\n链接：${book.url || '无'}`;
        navigator.clipboard.writeText(text).then(() => {
            const btn = e.currentTarget;
            btn.classList.add('copied');
            btn.textContent = '已复制';
            showToast('已复制');
            setTimeout(() => {
                btn.classList.remove('copied');
                btn.textContent = '复制信息';
            }, 1500);
        }).catch(() => {
            // Fallback for older browsers
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showToast('已复制');
        });
    }

    // ========== Mobile menu ==========
    let overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('show');
    });

    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    });

    // Escape 键关闭侧边栏
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
        }
    });

    // ========== Export Dropdown ==========
    const exportToggle = document.getElementById('export-toggle-btn');
    const exportMenu = document.getElementById('export-dropdown-menu');
    if (exportToggle && exportMenu) {
        exportToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            exportMenu.classList.toggle('show');
        });
        exportMenu.querySelectorAll('.export-btn-item').forEach(btn => {
            btn.addEventListener('click', () => {
                exportMenu.classList.remove('show');
                if (typeof exportData === 'function') {
                    exportData(btn.dataset.format, 'raw_rankings');
                }
            });
        });
        document.addEventListener('click', () => exportMenu.classList.remove('show'));
    }

    // ========== 搜索筛选排序 ==========
    const searchInput = document.getElementById('book-search');
    const filterSelect = document.getElementById('book-filter');
    const sortSelect = document.getElementById('book-sort');

    // 防抖搜索
    let searchTimer = null;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            if (searchTimer) clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                if (currentCategory) {
                    const cat = allData.categories.find(c => c.name === currentCategory);
                    if (cat) renderBooks(cat);
                }
            }, 200);
        });
    }

    if (filterSelect) {
        filterSelect.addEventListener('change', () => {
            if (currentCategory) {
                const cat = allData.categories.find(c => c.name === currentCategory);
                if (cat) renderBooks(cat);
            }
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            if (currentCategory) {
                const cat = allData.categories.find(c => c.name === currentCategory);
                if (cat) renderBooks(cat);
            }
        });
    }

    // parseReads 已移至 js/utils.js

    function getFilteredBooks(cat) {
        const changeMap = buildPrevRankMap(cat.name);
        let books = (cat.books || []).map((book, index) => ({
            ...book,
            rank: index + 1,
            change: changeMap[book.title] || null,
            readsNum: parseReads(book.reads)
        }));

        // 搜索过滤
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        if (query) {
            books = books.filter(b =>
                b.title.toLowerCase().includes(query) ||
                b.author.toLowerCase().includes(query)
            );
        }

        // 筛选
        const filter = filterSelect ? filterSelect.value : 'all';
        if (filter === 'new') {
            books = books.filter(b => b.change === 'new');
        } else if (filter === 'risers') {
            books = books.filter(b => b.change && b.change.startsWith('+'));
        } else if (filter === 'top10') {
            books = books.filter(b => b.rank <= 10);
        } else if (filter === 'top20') {
            books = books.filter(b => b.rank <= 20);
        }

        // 排序
        const sort = sortSelect ? sortSelect.value : 'rank';
        if (sort === 'reads') {
            books.sort((a, b) => b.readsNum - a.readsNum);
        } else if (sort === 'title') {
            books.sort((a, b) => a.title.localeCompare(b.title, 'zh'));
        }
        // sort === 'rank' 保持原序

        return books;
    }

    // ========== Date Navigation ==========
    function updateDateNav() {
        const isLatest = currentDateIndex === availableDates.length - 1;
        const isFirst = currentDateIndex <= 0;

        datePrevBtn.disabled = isFirst;
        dateNextBtn.disabled = isLatest;

        const currentDate = availableDates[currentDateIndex];
        dateDisplay.textContent = currentDate || '加载中...';

        // Highlight if viewing historical (non-latest) data
        if (isLatest) {
            datePickerBtn.classList.remove('is-historical');
        } else {
            datePickerBtn.classList.add('is-historical');
        }

        // Sync preset button active state
        updatePresetButtons();
    }

    // ========== Preset Buttons ==========
    const presetBtns = document.querySelectorAll('.preset-btn');

    function updatePresetButtons() {
        const isLatest = currentDateIndex === availableDates.length - 1;
        const isYesterday = availableDates.length >= 2 && currentDateIndex === availableDates.length - 2;

        presetBtns.forEach(btn => {
            const preset = btn.dataset.preset;
            if (preset === 'latest' && isLatest) {
                btn.classList.add('active');
            } else if (preset === 'yesterday' && isYesterday) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = btn.dataset.preset;
            if (preset === 'latest' && availableDates.length > 0) {
                currentDateIndex = availableDates.length - 1;
                loadDateData(availableDates[currentDateIndex]);
            } else if (preset === 'yesterday' && availableDates.length >= 2) {
                currentDateIndex = availableDates.length - 2;
                loadDateData(availableDates[currentDateIndex]);
            }
        });
    });

    datePrevBtn.addEventListener('click', () => {
        if (currentDateIndex > 0) {
            currentDateIndex--;
            loadDateData(availableDates[currentDateIndex]);
        }
    });

    dateNextBtn.addEventListener('click', () => {
        if (currentDateIndex < availableDates.length - 1) {
            currentDateIndex++;
            loadDateData(availableDates[currentDateIndex]);
        }
    });

    datePickerBtn.addEventListener('click', () => {
        // Trigger native date picker
        dateInput.showPicker ? dateInput.showPicker() : dateInput.click();
    });

    dateInput.addEventListener('change', () => {
        const selected = dateInput.value; // YYYY-MM-DD
        if (!selected) return;
        const idx = availableDates.indexOf(selected);
        if (idx !== -1) {
            currentDateIndex = idx;
            loadDateData(selected);
        } else if (availableDates.length > 0) {
            // Find nearest available date and show friendly hint
            const nearest = availableDates.reduce((prev, curr) =>
                Math.abs(new Date(curr) - new Date(selected)) < Math.abs(new Date(prev) - new Date(selected)) ? curr : prev
            );
            const nearIdx = availableDates.indexOf(nearest);
            currentDateIndex = nearIdx;
            loadDateData(nearest);
            showToast(`${selected} 无数据，已跳转至最近的 ${nearest}`);
        }
    });

    // ========== Load dates index, then load latest ==========
    // 显示骨架屏
    function showSkeletonLoading() {
        waterfall.innerHTML = Array(6).fill('').map(() =>
            '<div class="skeleton skeleton-card"></div>'
        ).join('');
        trendStats.innerHTML = Array(3).fill('').map(() =>
            '<span class="skeleton skeleton-chip"></span>'
        ).join('');
    }
    showSkeletonLoading();

    fetch(`data/dates_${prefix}.json?${cacheBuster}`)
        .then(r => r.ok ? r.json() : Promise.reject('No dates.json'))
        .then(idx => {
            availableDates = idx.dates || [];
            if (availableDates.length > 0) {
                // Set min/max for native date input
                dateInput.min = availableDates[0];
                dateInput.max = availableDates[availableDates.length - 1];
            }
            // Start by loading latest_ranks.json (already has trend data baked in)
            return loadLatestData();
        })
        .catch(() => {
            // Fallback: no dates.json available, just load latest
            console.warn(`dates_${prefix}.json not found, falling back to latest only`);
            // 确保 availableDates 是空数组，而不是 undefined
            if (!Array.isArray(availableDates)) {
                availableDates = [];
            }
            loadLatestData();
        });

    function loadLatestData() {
        return fetch(`data/latest_${prefix}_ranks.json?${cacheBuster}`)
            .then(r => {
                if (!r.ok) throw new Error('Network error');
                return r.json();
            })
            .then(data => {
                allData = data;
                // Set current index from dates list
                const latestDate = data.date;
                currentDateIndex = availableDates.indexOf(latestDate);
                if (currentDateIndex === -1) {
                    // Date might not be in index yet (e.g., dates.json not regenerated)
                    availableDates.push(latestDate);
                    availableDates.sort();
                    currentDateIndex = availableDates.indexOf(latestDate);
                }
                applyData(data);
            })
            .catch(err => {
                console.error(err);
                trendStats.innerHTML = '';
                waterfall.innerHTML = `
                    <div class="loading-state">
                        <p class="error-hint">数据加载失败</p>
                        <button class="retry-btn" onclick="location.reload()">点击重试</button>
                    </div>`;
            });
    }

    function loadDateData(dateStr) {
        // dateStr = "YYYY-MM-DD", file = fanqie_{prefix}_ranks_YYYYMMDD.json
        const fileDateStr = dateStr.replace(/-/g, '');
        const isLatest = currentDateIndex === availableDates.length - 1;

        if (isLatest) {
            // Just load the pre-built latest with trends
            loadLatestData();
            return;
        }

        // Show loading state
        waterfall.innerHTML = '<p style="color:var(--text-muted);padding:20px;">加载中...</p>';

        const snapshotUrl = `data/fanqie_${prefix}_ranks_${fileDateStr}.json?${cacheBuster}`;
        const trendUrl = `data/trends/${prefix}_${dateStr}.json?${cacheBuster}`;

        // Load snapshot + trends in parallel
        Promise.all([
            fetch(snapshotUrl).then(r => r.ok ? r.json() : Promise.reject('No snapshot')),
            fetch(trendUrl).then(r => r.ok ? r.json() : null).catch(() => null)
        ]).then(([snapshot, trendData]) => {
            // Build a data object in the same shape as latest_ranks.json
            const combined = {
                date: snapshot.date,
                prev_date: trendData ? trendData.prev_date : '',
                categories: snapshot.categories.map(cat => ({
                    name: cat.name,
                    trend: trendData && trendData.trends ? (trendData.trends[cat.name] || {}) : {},
                    books: cat.books || []
                }))
            };
            allData = combined;
            applyData(combined);
        }).catch(err => {
            console.error('Failed to load historical data:', err);
            const failedDate = availableDates[currentDateIndex] || dateStr;
            // Friendly no-data handler: auto-jump to nearest date
            const nearest = findNearestAvailableDate(failedDate);
            if (nearest && nearest !== failedDate) {
                showToast(`${failedDate} 数据不可用，已跳转至 ${nearest}`);
                currentDateIndex = availableDates.indexOf(nearest);
                loadDateData(nearest);
            } else {
                waterfall.innerHTML = `<div class="empty-state">
                    <p>📭 该日期（${failedDate}）暂无数据</p>
                    <p class="empty-hint">可尝试切换到其他日期查看</p>
                </div>`;
                updateDateNav();
            }
        });
    }

    function findNearestAvailableDate(targetDate) {
        // Try nearby dates, preferring the latest
        if (availableDates.length === 0) return null;
        return availableDates.reduce((prev, curr) =>
            Math.abs(new Date(curr) - new Date(targetDate)) < Math.abs(new Date(prev) - new Date(targetDate)) ? curr : prev
        );
    }

    function applyData(data) {
        const prevInfo = data.prev_date ? ` (对比 ${data.prev_date})` : '';
        updateDate.textContent = `${data.date}${prevInfo}`;
        updateDateNav();

        // 数据稀疏警告
        const sparseWarning = document.getElementById('sparse-warning');
        if (sparseWarning) sparseWarning.remove();
        if (availableDates.length > 0 && availableDates.length < 3) {
            const warn = document.createElement('div');
            warn.id = 'sparse-warning';
            warn.className = 'sparse-warning';
            warn.innerHTML = `<span class="warn-icon">⚠</span> 当前榜单仅有 ${availableDates.length} 天数据，趋势分析可能不够准确。数据积累中，请持续运行爬虫以获取更完整的分析。`;
            const mainContent = document.querySelector('.main-content');
            if (mainContent) mainContent.insertBefore(warn, mainContent.children[1]);
        }

        // 暴露数据给 export.js 使用
        window.authorData = Object.assign(window.authorData || {}, { latestRanks: data });

        // Remember current category before re-rendering
        const savedCategory = getCategoryFromURL() || currentCategory;
        renderCategories();

        // Try to restore previously selected category, otherwise pick first
        const categoryExists = savedCategory && data.categories.some(c => c.name === savedCategory);
        if (categoryExists) {
            selectCategory(savedCategory);
            // Also update sidebar active state
            document.querySelectorAll('#category-list li').forEach(el => {
                el.classList.toggle('active', el.dataset.category === savedCategory);
            });
        } else if (data.categories.length > 0) {
            selectCategory(data.categories[0].name);
            document.querySelectorAll('#category-list li').forEach((el, i) => {
                el.classList.toggle('active', i === 0);
            });
        }
    }

    // ========== Render sidebar categories ==========
    function renderCategories() {
        categoryList.innerHTML = '';
        allData.categories.forEach((cat, i) => {
            const li = document.createElement('li');
            li.dataset.category = cat.name;
            li.setAttribute('role', 'button');
            li.setAttribute('tabindex', '0');

            const nameSpan = document.createElement('span');
            nameSpan.textContent = cat.name;
            li.appendChild(nameSpan);

            // New entry badge
            const trend = cat.trend || {};
            if (trend.new_count > 0) {
                const badge = document.createElement('span');
                badge.className = 'cat-badge new';
                badge.textContent = `+${trend.new_count}`;
                li.appendChild(badge);
            }

            // Mark active: either the saved category or first item
            if ((currentCategory && cat.name === currentCategory) || (!currentCategory && i === 0)) {
                li.classList.add('active');
            }

            const activate = () => {
                document.querySelectorAll('#category-list li').forEach(el => el.classList.remove('active'));
                li.classList.add('active');
                selectCategory(cat.name);
                // Close mobile sidebar
                sidebar.classList.remove('open');
                overlay.classList.remove('show');
            };

            li.addEventListener('click', activate);
            li.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    activate();
                }
            });

            categoryList.appendChild(li);
        });
    }

    // ========== Select a category ==========
    function selectCategory(categoryName) {
        currentCategory = categoryName; // persist selection
        categoryTitle.textContent = categoryName;

        // 更新 URL 参数
        const url = new URL(window.location.href);
        url.searchParams.set('cat', categoryName);
        history.replaceState(null, '', url);

        const cat = allData.categories.find(c => c.name === categoryName);
        if (!cat) return;
        renderTrend(cat);
        renderBooks(cat);
    }

    // 从 URL 恢复分类选择
    function getCategoryFromURL() {
        const params = new URLSearchParams(window.location.search);
        return params.get('cat') || null;
    }

    // ========== Build a url->rank lookup for previous day ==========
    function buildPrevRankMap(categoryName) {
        // We infer prev rank from trend data
        // Actually, the trend data already has this info baked in.
        // For the card badges we need to know if a book is new or changed rank.
        const cat = allData.categories.find(c => c.name === categoryName);
        if (!cat || !cat.trend) return {};

        const map = {};
        // Mark new books
        (cat.trend.new_books || []).forEach(title => {
            map[title] = 'new';
        });
        // Risers
        (cat.trend.top_risers || []).forEach(r => {
            map[r.title] = r.change;
        });
        // Fallers
        (cat.trend.top_fallers || []).forEach(f => {
            map[f.title] = f.change;
        });
        return map;
    }

    // ========== Render Trend Panel ==========
    function renderTrend(cat) {
        const trend = cat.trend || {};
        trendStats.innerHTML = '';

        // Stat chips
        const chips = [];

        if (trend.new_count > 0) {
            chips.push({ icon: 'NEW', text: `${trend.new_count} 本新上榜`, cls: 'new-entry' });
        }
        if (trend.dropped_count > 0) {
            chips.push({ icon: 'OUT', text: `${trend.dropped_count} 本掉出`, cls: 'down' });
        }
        if (trend.top_risers && trend.top_risers.length > 0) {
            trend.top_risers.forEach(r => {
                chips.push({ icon: 'UP', text: `${r.title} ${r.change}`, cls: 'up' });
            });
        }
        if (trend.reads_growth && trend.reads_growth.length > 0) {
            chips.push({ icon: 'HOT', text: `${trend.reads_growth[0].title} ${trend.reads_growth[0].growth}`, cls: 'up' });
        }

        if (chips.length === 0) {
            chips.push({ icon: 'STABLE', text: '榜单无明显变动', cls: '' });
        }

        chips.forEach(chip => {
            const el = document.createElement('span');
            el.className = `stat-chip ${chip.cls}`;
            el.textContent = `${chip.icon} ${chip.text}`;
            trendStats.appendChild(el);
        });

        // AI Summary with typewriter effect
        const summary = trend.summary || '';
        renderAiContent(summary);
    }

    // renderMarkdown 已移至 js/utils.js

    // ========== AI 内容渲染 ==========
    function renderAiContent(text) {
        if (!text) {
            aiContent.innerHTML = '<span class="ai-loading">暂无分析数据</span>';
            return;
        }
        aiContent.innerHTML = renderMarkdown(text);
    }

    // escapeHtml 已移至 js/utils.js

    // ========== Render Books (Waterfall) ==========
    function renderBooks(cat) {
        waterfall.innerHTML = '';

        const books = getFilteredBooks(cat);

        if (books.length === 0) {
            const query = searchInput ? searchInput.value.trim() : '';
            const filter = filterSelect ? filterSelect.value : 'all';
            if (query) {
                waterfall.innerHTML = `<p style="color:var(--text-muted);padding:20px;">未找到匹配「${escapeHtml(query)}」的书籍。</p>`;
            } else if (filter !== 'all') {
                waterfall.innerHTML = '<p style="color:var(--text-muted);padding:20px;">当前筛选条件下暂无书籍。</p>';
            } else {
                waterfall.innerHTML = '<p style="color:var(--text-muted);padding:20px;">该分类暂无书籍。</p>';
            }
            return;
        }

        const fragment = document.createDocumentFragment();

        books.forEach((book) => {
            const card = document.createElement('a');
            card.href = book.url && book.url !== '#' ? book.url : 'javascript:void(0)';
            if (book.url && book.url !== '#') card.target = '_blank';
            card.rel = 'noopener';
            card.className = 'book-card';

            // Rank badge class
            let rankCls = '';
            if (book.rank === 1) rankCls = 'rank-1';
            else if (book.rank === 2) rankCls = 'rank-2';
            else if (book.rank === 3) rankCls = 'rank-3';

            // Change indicator
            let changeHtml = '';
            if (book.change === 'new') {
                changeHtml = '<span class="book-change new">NEW</span>';
            } else if (book.change && book.change.startsWith('+')) {
                changeHtml = `<span class="book-change up">↑${book.change}</span>`;
            } else if (book.change && book.change.startsWith('-')) {
                changeHtml = `<span class="book-change down">↓${book.change.replace('-', '')}</span>`;
            }

            // Cover
            const coverHtml = book.cover
                ? `<div class="book-cover"><img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}" loading="lazy"></div>`
                : `<div class="book-cover"><div class="no-cover">暂无封面</div></div>`;

            card.innerHTML = `
                <span class="book-rank ${rankCls}">${book.rank}</span>
                ${changeHtml}
                ${coverHtml}
                <div class="book-info">
                    <h3 class="book-title" title="${escapeAttr(book.title)}">${escapeHtml(book.title)}</h3>
                    <div class="book-meta">
                        <span class="book-author">${escapeHtml(book.author)}</span>
                        <span class="book-reads">${escapeHtml(book.reads)}</span>
                    </div>
                    <p class="book-intro">${escapeHtml(book.intro).replace(/\n/g, '<br>')}</p>
                    <button class="book-copy-btn" type="button">复制信息</button>
                </div>
            `;

            // Bind copy button
            const copyBtn = card.querySelector('.book-copy-btn');
            copyBtn.addEventListener('click', (e) => copyBookInfo(e, book));

            fragment.appendChild(card);
        });

        waterfall.appendChild(fragment);
    }

    // escapeAttr 已移至 js/utils.js
});
