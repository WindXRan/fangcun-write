document.addEventListener('DOMContentLoaded', () => {
    const rankConfig = getRankConfig();
    const prefix = rankConfig.prefix;

    const categoryList = document.getElementById('category-list');
    const waterfall = document.getElementById('books-waterfall');
    const updateDate = document.getElementById('update-date');
    const categoryTitle = document.getElementById('current-category-title');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');

    let allData = null;
    let currentCategory = null;

    const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;

    // ========== Copy Toast ==========
    function copyBookInfo(e, book) {
        e.preventDefault();
        e.stopPropagation();
        const text = `${book.title}\n作者：${book.author}\n状态：${book.status || '未知'}\n字数：${book.word_count || '未知'}\n最新章节：${book.last_chapter || '未知'}\n阅读量：${book.reads}\n简介：${book.intro || '无'}\n链接：${book.url || '无'}`;
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

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
        }
    });

    // ========== 搜索筛选排序 ==========
    const searchInput = document.getElementById('book-search');
    const filterSelect = document.getElementById('book-filter');
    const sortSelect = document.getElementById('book-sort');

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

    function getFilteredBooks(cat) {
        let books = (cat.books || []).map((book, index) => ({
            ...book,
            rank: index + 1,
            readsNum: parseReads(book.reads)
        }));

        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        if (query) {
            books = books.filter(b =>
                b.title.toLowerCase().includes(query) ||
                b.author.toLowerCase().includes(query)
            );
        }

        const filter = filterSelect ? filterSelect.value : 'all';
        if (filter === 'top10') {
            books = books.filter(b => b.rank <= 10);
        } else if (filter === 'top20') {
            books = books.filter(b => b.rank <= 20);
        } else if (filter === 'ongoing') {
            books = books.filter(b => b.status && b.status.includes('连载'));
        } else if (filter === 'finished') {
            books = books.filter(b => b.status && b.status.includes('完结'));
        }

        const sort = sortSelect ? sortSelect.value : 'rank';
        if (sort === 'reads') {
            books.sort((a, b) => b.readsNum - a.readsNum);
        } else if (sort === 'title') {
            books.sort((a, b) => a.title.localeCompare(b.title, 'zh'));
        } else if (sort === 'words') {
            books.sort((a, b) => {
                const wa = parseWordCount(a.word_count);
                const wb = parseWordCount(b.word_count);
                return wb - wa;
            });
        }

        return books;
    }

    // ========== 骨架屏 ==========
    function showSkeletonLoading() {
        waterfall.innerHTML = Array(6).fill('').map(() =>
            '<div class="skeleton skeleton-card"></div>'
        ).join('');
    }
    showSkeletonLoading();

    // ========== 只加载最新数据 ==========
    fetch(`data/latest_${prefix}_ranks.json?${cacheBuster}`)
        .then(r => {
            if (!r.ok) throw new Error('Network error');
            return r.json();
        })
        .then(data => {
            allData = data;
            applyData(data);
        })
        .catch(err => {
            console.error(err);
            waterfall.innerHTML = `
                <div class="loading-state">
                    <p class="error-hint">数据加载失败</p>
                    <button class="retry-btn" onclick="location.reload()">点击重试</button>
                </div>`;
        });

    function applyData(data) {
        const categories = data.categories || [];

        // 更新日期
        if (data.date) {
            updateDate.textContent = data.date;
        }

        // 渲染分类列表
        categoryList.innerHTML = '';

        // "全部分类" 选项
        const allItem = document.createElement('li');
        allItem.textContent = '全部分类';
        allItem.className = 'category-item' + (!currentCategory ? ' active' : '');
        allItem.addEventListener('click', () => {
            currentCategory = null;
            categoryTitle.textContent = '全部分类';
            renderAllCategories(categories);
            updateCategoryActive();
        });
        categoryList.appendChild(allItem);

        categories.forEach(cat => {
            const li = document.createElement('li');
            li.textContent = cat.name;
            li.className = 'category-item' + (currentCategory === cat.name ? ' active' : '');
            li.addEventListener('click', () => {
                currentCategory = cat.name;
                categoryTitle.textContent = cat.name;
                renderBooks(cat);
                updateCategoryActive();
            });
            categoryList.appendChild(li);
        });

        function updateCategoryActive() {
            categoryList.querySelectorAll('.category-item').forEach((item, i) => {
                if (i === 0) {
                    item.className = 'category-item' + (!currentCategory ? ' active' : '');
                } else {
                    const cat = categories[i - 1];
                    item.className = 'category-item' + (currentCategory === cat.name ? ' active' : '');
                }
            });
        }

        // 默认显示全部分类
        if (!currentCategory) {
            renderAllCategories(categories);
        } else {
            const cat = categories.find(c => c.name === currentCategory);
            if (cat) renderBooks(cat);
            else renderAllCategories(categories);
        }
    }

    function renderAllCategories(categories) {
        waterfall.innerHTML = '';
        categories.forEach(cat => {
            const section = document.createElement('div');
            section.className = 'category-section';

            const header = document.createElement('div');
            header.className = 'category-section-header';
            header.innerHTML = `<h3>${escapeHtml(cat.name)}</h3><span class="category-count">${(cat.books || []).length} 本</span>`;
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                currentCategory = cat.name;
                categoryTitle.textContent = cat.name;
                renderBooks(cat);
            });
            section.appendChild(header);

            const preview = document.createElement('div');
            preview.className = 'books-waterfall';
            const books = (cat.books || []).slice(0, 5);
            books.forEach((book, i) => {
                preview.appendChild(createBookCard(book, i + 1));
            });
            section.appendChild(preview);

            waterfall.appendChild(section);
        });
    }

    function renderBooks(cat) {
        const books = getFilteredBooks(cat);
        waterfall.innerHTML = '';

        if (books.length === 0) {
            waterfall.innerHTML = '<div class="empty-state"><p>没有匹配的书籍</p></div>';
            return;
        }

        books.forEach(book => {
            waterfall.appendChild(createBookCard(book, book.rank));
        });
    }

    function createBookCard(book, rank) {
        const card = document.createElement('div');
        card.className = 'book-card';

        const coverHtml = book.cover
            ? `<div class="book-cover"><img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}" loading="lazy" onerror="this.style.display='none';this.parentElement.innerHTML='<div class=\\'no-cover\\'>暂无封面</div>'"></div>`
            : `<div class="book-cover"><div class="no-cover">暂无封面</div></div>`;

        const statusBadge = book.status
            ? `<span class="book-status ${book.status.includes('完结') ? 'finished' : 'ongoing'}">${escapeHtml(book.status)}</span>`
            : '';

        const wordCountHtml = book.word_count
            ? `<span class="book-words">${escapeHtml(book.word_count)}</span>`
            : '';

        const chapterHtml = book.last_chapter
            ? `<div class="book-chapter">最新：${escapeHtml(book.last_chapter)}</div>`
            : '';

        card.innerHTML = `
            <div class="book-rank">${rank}</div>
            ${coverHtml}
            <div class="book-info">
                <div class="book-title-row">
                    <a class="book-title" href="${escapeAttr(book.url || '#')}" target="_blank" rel="noopener">${escapeHtml(book.title)}</a>
                    ${statusBadge}
                </div>
                <div class="book-meta">
                    <span class="book-author">${escapeHtml(book.author)}</span>
                    ${wordCountHtml}
                    <span class="book-reads">${escapeHtml(book.reads || '')}</span>
                </div>
                <div class="book-intro">${escapeHtml((book.intro || '').slice(0, 120))}</div>
                ${chapterHtml}
                <div class="book-actions">
                    <button class="copy-btn" onclick="arguments[0].stopPropagation()">复制信息</button>
                </div>
            </div>
        `;

        const copyBtn = card.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', (e) => copyBookInfo(e, book));
        }

        return card;
    }

    function showToast(msg) {
        let toast = document.querySelector('.toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    }
});
