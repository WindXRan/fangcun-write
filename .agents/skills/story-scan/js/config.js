/* ============================================================
   榜单类型注册表 + URL参数解析
   所有页面共享此配置，通过 ?rank= 参数确定当前榜单
   ============================================================ */

const RANK_TYPES = {
    male_new:    { name: "男频新书榜", prefix: "male_new",    gender: "男频" },
    male_read:   { name: "男频阅读榜", prefix: "male_read",   gender: "男频" },
    female_new:  { name: "女频新书榜", prefix: "female_new",  gender: "女频" },
    female_read: { name: "女频阅读榜", prefix: "female_read", gender: "女频" },
};

const DEFAULT_RANK_TYPE = "female_new";

function getRankTypeFromURL() {
    const params = new URLSearchParams(window.location.search);
    const rank = params.get("rank");
    return RANK_TYPES[rank] ? rank : DEFAULT_RANK_TYPE;
}

function getRankConfig() {
    return RANK_TYPES[getRankTypeFromURL()];
}

// 为当前页面URL设置rank参数，用于导航切换
function buildPageURL(rankType) {
    const url = new URL(window.location.href);
    url.searchParams.set("rank", rankType);
    return url.pathname + url.search;
}

// 页面加载后，为所有硬编码的导航链接追加当前 rank 参数
document.addEventListener('DOMContentLoaded', () => {
    const currentRank = getRankTypeFromURL();
    document.querySelectorAll('.trend-link-btn[href]').forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.includes('rank=')) {
            const sep = href.includes('?') ? '&' : '?';
            link.setAttribute('href', `${href}${sep}rank=${currentRank}`);
        }
    });
});
