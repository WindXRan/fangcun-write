/**
 * 共享工具函数 — 供 app.js / trend.js / author.js / export.js 使用
 */

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:1.05rem; margin:1em 0 0.5em; color:var(--text-primary);">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:1.15rem; margin:1em 0 0.5em; color:var(--text-primary);">$1</h2>');
    // 先用占位符替换 **粗体**，再处理 *斜体*，避免正则冲突
    const boldPlaceholders = [];
    html = html.replace(/\*\*(.+?)\*\*/g, (match, p1) => {
        const ph = `\x00B${boldPlaceholders.length}\x00`;
        boldPlaceholders.push(`<strong>${p1}</strong>`);
        return ph;
    });
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    // 还原粗体占位符
    boldPlaceholders.forEach((replacement, i) => {
        html = html.replace(`\x00B${i}\x00`, replacement);
    });
    html = html.replace(/《(.+?)》/g, '<span style="color:var(--accent);font-weight:500">《$1》</span>');
    html = html.replace(/^[-*] (.+)$/gm, '<span style="display:block;padding-left:1em;text-indent:-0.6em">• $1</span>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<span style="display:block;padding-left:1em;text-indent:-0.6em">$1. $2</span>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function parseReads(readsStr) {
    if (!readsStr || readsStr === '未知') return 0;
    const s = readsStr.replace(/,/g, '');
    if (s.includes('万')) return parseFloat(s.replace('万', '')) * 10000;
    return parseFloat(s) || 0;
}
