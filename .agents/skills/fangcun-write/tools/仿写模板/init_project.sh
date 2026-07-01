#!/bin/bash
# 初始化仿写项目结构 — 创建完整的三纲+设定目录
# 用法: bash init_project.sh <项目名> <源书名>

PROJECT=$1
SOURCE=$2
BASE="projects/$PROJECT"

if [ -z "$PROJECT" ]; then
  echo "用法: bash init_project.sh <项目名> <源书名>"
  echo "示例: bash init_project.sh 我的仿写书 全家偷听心声"
  exit 1
fi

echo "创建项目: $PROJECT"

# 目录结构
mkdir -p "$BASE/作品信息/主题"
mkdir -p "$BASE/作品信息/设定/角色"
mkdir -p "$BASE/作品信息/设定/势力"
mkdir -p "$BASE/作品信息/设定/地点"
mkdir -p "$BASE/作品信息/设定/物品"
mkdir -p "$BASE/作品信息/设定/背景"
mkdir -p "$BASE/正文/卷纲"
mkdir -p "$BASE/正文/章纲"
mkdir -p "$BASE/正文/正文"
mkdir -p "$BASE/_debug"

echo "目录结构 ✅"

# project.xml
cat > "$BASE/作品信息/project.xml" << EOF
<?xml version='1.0' encoding='utf-8'?>
<project>
  <story_name>$PROJECT</story_name>
  <channel>女频</channel>
  <perspective>第三人称</perspective>
  <author>仿写</author>
  <total_chapters>200</total_chapters>
  <source_book>$SOURCE</source_book>
</project>
EOF
echo "project.xml ✅"

# 总纲模板（7节格式）
cat > "$BASE/作品信息/主题/总纲.xml" << 'EOF'
<story_bible tool="open-book">
  <section name="书名与作品定位">
    <recommended_titles>
      <title>书名</title>
    </recommended_titles>
    <genre>古代权谋 | 系统流 | 家庭守护</genre>
    <platform>番茄</platform>
    <core_emotion>甜宠、热血、治愈</core_emotion>
    <hook>一句话钩子</hook>
  </section>
  <section name="核心人设与故事根基">
    <protagonist>
      <name>主角名</name>
      <status>当前处境</status>
      <desire>最想要什么</desire>
      <fear>最怕失去什么</fear>
      <ability>核心能力</ability>
      <weakness>核心短板</weakness>
      <why_irreplaceable>为什么必须是她</why_irreplaceable>
      <support_point>人设支撑点</support_point>
    </protagonist>
    <family>
      <member name="父亲名" role="父亲">功能定位</member>
      <member name="母亲名" role="母亲">功能定位</member>
      <member name="大哥名" role="大哥">功能定位</member>
      <member name="二哥名" role="二哥">功能定位</member>
    </family>
    <love_interest name="男主名" role="核心CP">功能定位</love_interest>
  </section>
  <section name="古代题材与时代秩序">
    <dynasty>朝代设定</dynasty>
    <social_order>
      <item>社会规则1</item>
      <item>社会规则2</item>
    </social_order>
    <system_integration>金手指的定位和限制</system_integration>
  </section>
  <section name="贯穿全文的核心设定">
    <core_premise>核心设定一句话</core_premise>
    <evolution>
      <phase n="1" chapters="1-50">前期</phase>
      <phase n="2" chapters="51-120">中期</phase>
      <phase n="3" chapters="121-200">后期</phase>
    </evolution>
  </section>
  <section name="人物关系与主要推动力/阻力">
    <driving_forces>
      <external>外部推动力</external>
      <internal>内部推动力</internal>
    </driving_forces>
    <obstacles>
      <item>核心阻力</item>
    </obstacles>
  </section>
  <section name="故事总纲">
    <volume n="1" start="1" end="50" title="第一卷">
      <summary>本卷核心冲突</summary>
      <opening>第一章开场事件</opening>
      <first_3_chapters>前三章任务</first_3_chapters>
      <climax>卷高潮</climax>
      <hook>卷尾钩子</hook>
    </volume>
    <volume n="2" start="51" end="120" title="第二卷">
      <summary>本卷核心冲突</summary>
    </volume>
    <volume n="3" start="121" end="200" title="第三卷">
      <summary>本卷核心冲突</summary>
    </volume>
  </section>
  <section name="写作风格与禁区">
    <style_rules>
      <rule>风格要求</rule>
    </style_rules>
    <forbidden>
      <item>禁止事项</item>
    </forbidden>
  </section>
</story_bible>
EOF
echo "总纲模板 ✅"

# 简介模板（纯文本格式）
cat > "$BASE/作品信息/主题/简介.xml" << 'EOF'
穿进即将满门抄斩的虐文里，主角刚出生就发现全家都能听见她的吐槽。她骂丫鬟是内鬼，第二天丫鬟就被发卖。她八卦大哥的官配是谁，没过几天未来大嫂就上了门。她忧虑全家死期将至，她爹就连夜把未来大反派给告了。主角以为自己是全家唯一手握剧本的人，却不知道全家早就知道她有预知能力，还配合她演了这么多年。

———

穿书女婴×全家偷听心声/温馨团宠与逆天改命双线并行/智商在线不降智
EOF
echo "简介模板 ✅"

# 标签模板
cat > "$BASE/作品信息/主题/标签.xml" << 'EOF'
<tags>
  <tag category="题材">穿书 | 系统 | 权谋 | 团宠</tag>
  <tag category="情绪">甜宠 | 热血 | 治愈</tag>
  <tag category="节奏">群像 | 剧情流</tag>
  <tag category="平台">番茄</tag>
</tags>
EOF
echo "标签模板 ✅"

# 卷纲模板
for v in 1 2 3; do
cat > "$BASE/正文/卷纲/第${v}卷.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<volume id="$v" name="第${v}卷" start="$(( (v-1) * 60 + 1 ))" end="$(( v * 60 ))">
  <summary>本卷核心任务一句话。主角面临什么困境、做了什么、家人各自的作用。几个关键转折。高潮事件。卷尾钩子。</summary>
</volume>
EOF
done
echo "卷纲 ✅"

# 角色卡模板
for role in 主角名 母亲名 父亲名 大哥名 二哥名 男主名; do
cat > "$BASE/作品信息/设定/角色/${role}.xml" << EOF
<character name="${role}" tier="main" role="protagonist" gender="女" age="0岁">
  <tags>标签1 | 标签2</tags>
  <core>
    <core_desire>核心欲望</core_desire>
    <core_fear>核心恐惧</core_fear>
    <core_value>核心价值观</core_value>
    <core_contrast>核心反差</core_contrast>
  </core>
  <language_style>
    <trait name="口癖">口癖词</trait>
    <trait name="节奏">说话节奏</trait>
    <trait name="信息偏好">信息偏好</trait>
    <trait name="立场">立场</trait>
    <trait name="身份措辞">措辞风格</trait>
    <trait name="性格语气">语气特征</trait>
    <trait name="进度态度">推进态度</trait>
  </language_style>
  <arc>
    <start>起点</start>
    <turning_point>转折</turning_point>
    <end>终点</end>
  </arc>
  <bio>人物小传</bio>
</character>
EOF
done
echo "角色卡模板 ✅"

# 设定模板
echo '<location name="主场景"><description>场景描述</description></location>' > "$BASE/作品信息/设定/地点/主场景.xml"
echo '<item name="金手指"><description>系统描述</description></item>' > "$BASE/作品信息/设定/物品/金手指.xml"
echo '<setting name="世界观"><description>世界观描述</description></setting>' > "$BASE/作品信息/设定/背景/世界观.xml"

echo ""
echo "==================================="
echo "项目初始化完成: $PROJECT"
echo "源书: $SOURCE"
echo "需要手动填入的内容:"
echo "  1. 总纲 - 书名、人设、剧情"
echo "  2. 角色卡 - 每个角色的具体设定"
echo "  3. 地点/物品/背景 - 世界观的细节"
echo "  4. 卷纲 - 每卷的叙事流描述"
echo "  5. 章纲 - 用 source-guide-reverse 从源书逆推"
echo "==================================="
