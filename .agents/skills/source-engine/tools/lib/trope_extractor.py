"""从源文动态提取梗/意象关键词，替代硬编码模式。

用法：
    from lib.trope_extractor import extract_tropes_from_source, extract_imagery_from_source
    
    tropes = extract_tropes_from_source(source_text)  # 返回 {类别: [模式列表]}
    imagery = extract_imagery_from_source(source_text)  # 返回 [关键词列表]
"""

import re
from collections import Counter


# 通用梗/桥段模式（不含具体人名/物名，适用于任何题材）
GENERIC_TROPE_CATEGORIES = {
    "吃东西": [
        r"吃[了着过]?\w{1,4}",
        r"喝[了着过]?\w{1,4}",
        r"馋[了着嘴]?",
        r"肚子[饿叫咕]",
        r"嘴[角唇]?\w{0,2}(?:笑|翘|撇|抿)",
    ],
    "身体反应": [
        r"眼[眶圈睛]\w{0,2}(?:红|湿|润|酸)",
        r"泪[水珠]?\w{0,2}(?:滑|落|掉|涌|忍)",
        r"心[里中底]\w{0,2}(?:一[沉颤揪]|[沉跳慌酸痛堵]",
        r"手[指掌拳]\w{0,2}(?:攥|握|紧|松|抖|颤)",
        r"肩膀\w{0,2}(?:抖|颤|耸|塌)",
    ],
    "情绪表达": [
        r"(?:深|长|轻|缓)[深长轻缓]?[吸呼]了?一?口?气?",
        r"愣[了住]?一?[下秒瞬间]",
        r"回[过到]神[来]?",
        r"心[里中底]?(?:暗想|琢磨|盘算|寻思)",
        r"(?:忍不|忍住|没忍)[住住]?[地的]?\w{0,2}(?:笑|哭|叹|叫|喊)",
    ],
    "环境描写": [
        r"窗外\w{0,4}(?:阳光|月光|星光|灯火|雨|雪|风)",
        r"(?:阳光|月光|星光)\w{0,4}(?:洒|照|落|透|映)",
        r"(?:蝉|蛙|鸟|虫)[鸣叫啼]\w{0,2}(?:声|响)",
        r"(?:树叶|花瓣|落叶|雪花)\w{0,2}(?:飘|落|飞|舞|散)",
    ],
    "对话互动": [
        r"(?:说|道|问|答|喊|叫|骂|笑)\w{0,2}(?:道|说|着)",
        r"(?:沉默|静[默了]?)\w{0,2}(?:片刻|一会|半晌|良久)",
        r"(?:张了张|动了动)\w{0,2}(?:嘴|唇|口)",
        r"(?:欲言|话到)\w{0,2}(?:又止|嘴边|嘴)",
    ],
    "动作描写": [
        r"(?:转[过身]?|[回扭]过)\w{0,2}(?:头|身|脸|去)",
        r"(?:走[到进]?|[迈踏])\w{0,2}(?:步|脚|进|出)",
        r"(?:拿[起出]?|[掏摸]出)\w{0,2}(?:来|起|出)",
        r"(?:放[下到]?|[搁置]下)\w{0,2}(?:来|起|下)",
    ],
}


def extract_tropes_from_source(source_text, min_count=3):
    """从源文提取高频梗/桥段模式。
    
    Args:
        source_text: 源文文本
        min_count: 最小出现次数（低于此数的模式不提取）
    
    Returns:
        dict: {类别: [(模式, 次数), ...]}
    """
    results = {}
    for category, patterns in GENERIC_TROPE_CATEGORIES.items():
        found = []
        for pattern in patterns:
            matches = re.findall(pattern, source_text)
            if len(matches) >= min_count:
                found.append((pattern, len(matches)))
        if found:
            found.sort(key=lambda x: -x[1])
            results[category] = found
    return results


def extract_imagery_from_source(source_text, min_count=2):
    """从源文提取环境意象关键词。
    
    使用通用意象词库 + 动态提取。
    
    Args:
        source_text: 源文文本
        min_count: 最小出现次数
    
    Returns:
        list: [关键词列表]
    """
    # 通用意象词库
    imagery_base = [
        # 植物
        '树', '花', '草', '叶', '枝', '根', '藤', '竹', '柳', '松', '柏',
        '槐', '杏', '桃', '梨', '枣', '梅', '兰', '菊', '荷', '莲',
        # 自然现象
        '阳光', '月光', '星光', '灯火', '烛光',
        '雨', '雪', '风', '霜', '雾', '露', '云',
        '雷', '电', '虹', '霞',
        # 动物
        '鸟', '鱼', '虫', '蝶', '蜂', '蝉', '蛙', '猫', '狗',
        '燕', '雀', '鹰', '鸡', '鸭', '鹅',
        # 水相关
        '水', '河', '溪', '湖', '井', '泉', '池', '塘',
        # 建筑/器物
        '窗', '门', '墙', '院', '巷', '街', '路',
        '灯', '烛', '茶', '酒', '烟',
        # 天体
        '日', '月', '星', '天',
    ]
    
    # 提取实际出现的意象
    found_imagery = []
    for word in imagery_base:
        if len(word) >= 2:  # 至少2字
            count = source_text.count(word)
            if count >= min_count:
                found_imagery.append(word)
    
    # 提取"X+的+Y"格式的意象短语（如"歪脖子树"、"老槐树"）
    imagery_phrases = re.findall(r'[\u4e00-\u9fa5]{1,3}(?:的|之)?[\u4e00-\u9fa5]{1,2}(?:树|花|草|叶|光|影|声|色|香)', source_text)
    phrase_counter = Counter(imagery_phrases)
    for phrase, count in phrase_counter.items():
        if count >= min_count and phrase not in found_imagery:
            found_imagery.append(phrase)
    
    return found_imagery


def extract_character_names_from_source(source_text):
    """从源文提取人名（通用模式）。
    
    Returns:
        list: [人名列表]
    """
    # 中文姓名模式：姓(1字) + 名(1-2字)
    # 常见姓氏
    common_surnames = (
        '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜'
        '戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐'
        '费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄'
        '和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁'
        '杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍'
        '虞万支柯管卢莫经房裘干解应宗丁宣邓单杭洪包诸左石崔吉龚程嵇邢滑裴陆'
        '荣翁荀羊甄家封芮靳邴松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋'
        '仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟溥印宿白怀蒲'
    )
    
    # 匹配姓+名（1-2字名）
    pattern = f'[{common_surnames}][\u4e00-\u9fa5]{{1,2}}'
    names = re.findall(pattern, source_text)
    
    # 过滤常见非人名词汇
    exclude_words = {
        '中国', '北京', '上海', '广州', '深圳', '天津', '重庆',
        '春天', '夏天', '秋天', '冬天', '早上', '中午', '晚上',
        '今天', '明天', '昨天', '后天', '前天',
        '先生', '女士', '小姐', '师傅', '老师', '同学',
        '爸爸', '妈妈', '爷爷', '奶奶', '哥哥', '姐姐',
    }
    
    # 统计频率，取高频词作为人名
    name_counter = Counter(names)
    likely_names = [
        name for name, count in name_counter.items()
        if count >= 3 and name not in exclude_words and len(name) >= 2
    ]
    
    return likely_names


def get_trope_patterns_for_validation(config, source_text=None):
    """获取用于验证的梗模式（兼容旧接口）。
    
    Returns:
        dict: {类别: [正则模式列表]}
    """
    if source_text is None:
        from utils import get_source_text
        # 读取前3章源文作为样本
        sample = ""
        for ch in range(1, 4):
            text = get_source_text(config, ch)
            if text:
                sample += text + "\n"
        source_text = sample
    
    tropes = extract_tropes_from_source(source_text, min_count=2)
    
    # 转换为旧格式 {类别: [模式列表]}
    result = {}
    for category, pattern_counts in tropes.items():
        result[category] = [p for p, c in pattern_counts]
    
    return result


def get_imagery_keywords_for_review(config, source_text=None):
    """获取用于审查的意象关键词（兼容旧接口）。
    
    Returns:
        list: [关键词列表]
    """
    if source_text is None:
        from utils import get_source_text
        # 读取前3章源文作为样本
        sample = ""
        for ch in range(1, 4):
            text = get_source_text(config, ch)
            if text:
                sample += text + "\n"
        source_text = sample
    
    return extract_imagery_from_source(source_text, min_count=2)
