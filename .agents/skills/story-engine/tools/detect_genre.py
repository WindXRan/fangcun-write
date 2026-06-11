"""
品类自动检测（LLM 版）：读源文首章 + header，让 LLM 判断品类。

用法：
    genre = detect_genre(config, api_key)
"""
import json
import os
import sys
from pathlib import Path


SYSTEM_PROMPT = "你是一个网文品类分析师。只输出一个品类词，不要解释。"


USER_PROMPT = """读下面的源文信息，判断这本书的**品类归属**。

品类是写法和读者预期的标签，不是题材标签。

参考品类（示例，不限于此）：
- **都市擦边**：男频，都市背景，系统/后宫/多女主，擦边浓度高
- **修仙升级**：男频，玄幻/修仙背景，修炼升级打怪
- **都市系统**：男频，都市背景，系统文，擦边浓度低
- **古言甜宠**：女频，古代背景，男女主感情线
- **现言甜宠**：女频，现代背景，男女主感情线
- **脑洞无敌流**：男频，脑洞设定+无敌+搞笑

**如果以上都不匹配，根据源文特征创建一个新的品类名。**

输出要求：
- 仅一个品类词（4字以内）
- 不要解释
- 如果无法判断，输出"通用"

--- 源文信息 ---

分类：{category}
标签：{tags}

简介：
{intro}

首章开头500字：
{ch_start}

--- 输出 ---"""


def read_source_info(source_dir):
    """读 source info"""
    header_path = Path(source_dir).parent / "_header.txt"
    category = ""
    tags = []
    intro = ""
    ch_start = ""

    if header_path.exists():
        text = header_path.read_text(encoding="utf-8")
        in_intro = False
        for line in text.splitlines():
            sep = "：" if "：" in line else ":"
            if line.startswith("分类"):
                category = line.split(sep, 1)[-1].strip()
            if line.startswith("标签"):
                raw = line.split(sep, 1)[-1].strip()
                tags = [t.strip() for t in raw.split("|")]
            if line.startswith("简介"):
                in_intro = True
                continue
            if in_intro:
                if line.startswith("==="):
                    break
                intro += line

    # 首章500字
    chap_dir = Path(source_dir)
    if chap_dir.exists():
        ch_files = sorted(chap_dir.glob("第*章.txt"))
        if not ch_files:
            ch_files = sorted(chap_dir.glob("*.txt"))
        if ch_files:
            try:
                full = ch_files[0].read_text(encoding="utf-8")
                ch_start = full[:500]
            except Exception:
                pass

    return category, tags, intro, ch_start


def detect_genre(config, api_key=None):
    """LLM 检测品类。"""
    base_dir = config.get("base_dir", os.getcwd())
    source_dir = config.get("source_chapter_dir", "")
    if not source_dir:
        return ""

    source_dir = str(Path(base_dir) / source_dir) if not Path(source_dir).is_absolute() else source_dir
    category, tags, intro, ch_start = read_source_info(source_dir)

    prompt = USER_PROMPT.format(
        category=category or "（未知）",
        tags=" | ".join(tags) if tags else "（无标签）",
        intro=(intro or "（无简介）").strip(),
        ch_start=(ch_start or "（无内容）").strip(),
    )

    api_key = api_key or os.environ.get("API_KEY")
    model = config.get("detect_model", "deepseek-v4-flash")

    result = _call_llm(prompt, api_key, model)
    if not result:
        return ""

    # 清理输出：去标点、去空白、去小尾巴
    genre = re.sub(r"[。，.,、！!？?\n\r\s]", "", result).strip()

    # 过滤非法品类名
    if not genre or len(genre) < 2:
        return ""
    if not all("\u4e00" <= c <= "\u9fff" for c in genre):
        return ""

    # 品类名归一化：别名 → 标准名
    genre = _normalize_genre(genre)

    return genre


def _normalize_genre(genre):
    """通过 config/genre_aliases.json 做别名归一化。

    如果 genre 匹配任意别名 → 返回对应的标准名。
    无匹配 → 写入 alias 文件（自动注册新品类），返回原值。
    """
    aliases_path = Path(__file__).parent.parent / "config" / "genre_aliases.json"
    if not aliases_path.exists():
        return genre

    try:
        alias_map = json.loads(aliases_path.read_text(encoding="utf-8"))
    except Exception:
        return genre

    for canonical, alias_list in alias_map.items():
        if genre == canonical:
            return canonical
        if genre in alias_list:
            return canonical

    # 新品类 → 自动注册到 alias 文件
    alias_map[genre] = [genre]
    try:
        aliases_path.write_text(
            json.dumps(alias_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return genre


def _call_llm(prompt, api_key, model="deepseek-v4-flash"):
    """轻量 LLM 调用，复用 lib/api_client 的配置"""
    from lib.api_client import get_api_url

    api_url = get_api_url({"api_key": api_key})

    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个网文品类分析师。只输出一个词。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2000,
        "temperature": 0,
    }).encode("utf-8")

    try:
        import urllib.request
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read().decode("utf-8"))
        raw = body["choices"][0]["message"]["content"]
        # 不 strip，保留原始内容做验证
        return raw
    except Exception as e:
        print(f"  [WARN] LLM genre detection failed: {e}")
        return ""


if __name__ == "__main__":
    import json as _json
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if cfg_path:
        cfg = _json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        print(f"检测品类: {detect_genre(cfg)}")
    else:
        # test with default project
        test = {
            "source_chapter_dir": "projects/今入画/执掌女监，女犯看我心慌慌！/_cache/chapters",
            "channel": "male"
        }
        print(f"检测品类: {detect_genre(test)}")
