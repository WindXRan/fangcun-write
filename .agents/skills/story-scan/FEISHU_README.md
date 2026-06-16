# 飞书同步功能使用指南

## 简介

飞书同步功能可以将story-scan采集的数据自动同步到飞书在线表格，方便团队协作和数据分析。

## 前置条件

1. **飞书开放平台账号**
   - 访问 [飞书开放平台](https://open.feishu.cn/) 注册账号
   - 创建企业自建应用

2. **飞书在线表格**
   - 在飞书中创建一个在线表格
   - 记录表格的token和工作表ID

3. **Python环境**
   - Python 3.9+
   - 已安装项目依赖

## 配置步骤

### 第一步：创建飞书应用

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 点击"创建企业自建应用"
3. 填写应用名称和描述
4. 记录App ID和App Secret

### 第二步：配置应用权限

1. 在应用详情页面，点击"权限管理"
2. 添加以下权限：
   - `sheets:spreadsheet` - 读写表格
   - `sheets:spreadsheet:readonly` - 只读表格（可选）
3. 发布应用版本

### 第三步：获取表格信息

1. 在飞书中创建或打开一个在线表格
2. 从URL中获取表格token：
   ```
   https://xxx.feishu.cn/sheets/【表格token】
   ```
3. 获取工作表ID：
   - 在表格底部，右键点击工作表标签
   - 选择"复制工作表ID"

### 第四步：配置环境变量

#### Windows PowerShell
```powershell
$env:FEISHU_APP_ID="your-app-id"
$env:FEISHU_APP_SECRET="your-app-secret"
$env:FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"
$env:FEISHU_SHEET_ID="your-sheet-id"
```

#### Windows CMD
```cmd
set FEISHU_APP_ID=your-app-id
set FEISHU_APP_SECRET=your-app-secret
set FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token
set FEISHU_SHEET_ID=your-sheet-id
```

#### Linux/Mac
```bash
export FEISHU_APP_ID="your-app-id"
export FEISHU_APP_SECRET="your-app-secret"
export FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"
export FEISHU_SHEET_ID="your-sheet-id"
```

#### 或创建.env文件
在 `.agents/skills/story-scan/.env` 文件中添加：
```
FEISHU_APP_ID=your-app-id
FEISHU_APP_SECRET=your-app-secret
FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token
FEISHU_SHEET_ID=your-sheet-id
```

## 使用方法

### 快速测试

```bash
cd .agents/skills/story-scan

# 测试配置
python test_feishu_sync.py

# 快速测试
python quick_test.py
```

### 同步数据

```bash
# 方法一：使用一键脚本
python run.py sync-feishu

# 方法二：直接运行同步脚本
python feishu_sync.py

# 方法三：测试模式（只读取数据不写入）
python feishu_sync.py --test
```

### 查看使用示例

```bash
python example_feishu_sync.py
```

## 同步的数据

飞书同步功能会同步以下数据到表格：

### 1. 排行榜数据（A-H列）
| 列 | 内容 |
|----|------|
| A | 排名 |
| B | 书名 |
| C | 作者 |
| D | 阅读量 |
| E | 状态 |
| F | 字数 |
| G | 最后更新 |
| H | 简介 |

### 2. 市场总结（J-L列）
| 列 | 内容 |
|----|------|
| J | 市场总结标题 |
| K | 日期 |
| L | 时间段 |

### 3. 市场数据（N-S列）
| 列 | 内容 |
|----|------|
| N | 热门题材 |
| O | 热度 |
| P | 趋势 |
| Q | 竞争程度 |
| R | 描述 |
| S | 代表作品 |

## 故障排除

### 问题1：导入失败
```
ImportError: No module named 'requests'
```
**解决方案：**
```bash
pip install requests
```

### 问题2：获取token失败
```
获取token失败: app access token is invalid
```
**解决方案：**
1. 检查App ID和App Secret是否正确
2. 确认应用已发布版本
3. 检查应用权限是否配置正确

### 问题3：写入表格失败
```
写入表格失败: permission denied
```
**解决方案：**
1. 检查应用是否有表格读写权限
2. 确认表格token和工作表ID正确
3. 确认应用已添加到表格的协作者

### 问题4：数据格式错误
```
写入表格失败: invalid value range
```
**解决方案：**
1. 检查数据文件是否存在
2. 确认数据格式正确
3. 检查表格是否有足够的列

## 高级用法

### 自定义同步逻辑

如果需要同步其他数据，可以修改 `feishu_sync.py` 文件：

1. **修改数据格式**
   - 编辑 `prepare_rank_data()` 函数
   - 编辑 `prepare_summary_data()` 函数
   - 编辑 `prepare_market_data()` 函数

2. **修改同步逻辑**
   - 编辑 `sync_to_feishu()` 函数
   - 添加新的数据类型同步

3. **添加新的数据源**
   - 在 `load_latest_data()` 函数中添加新的数据文件

### 定时自动同步

#### Windows任务计划程序
1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天定时）
4. 设置操作（运行Python脚本）

#### Linux/Mac Cron
```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天早上8点同步）
0 8 * * * cd /path/to/.agents/skills/story-scan && python run.py sync-feishu
```

## API参考

### FeishuSync类

#### 方法
- `get_tenant_access_token()` - 获取访问token
- `read_sheet_data(range_str)` - 读取表格数据
- `write_sheet_data(range_str, values)` - 写入表格数据
- `append_sheet_data(range_str, values)` - 追加表格数据
- `clear_sheet_data(range_str)` - 清空表格数据

### 数据准备函数

- `prepare_rank_data(rank_data)` - 准备排行榜数据
- `prepare_summary_data(summary_data)` - 准备市场总结数据
- `prepare_market_data(market_data)` - 准备市场数据

## 相关链接

- [飞书开放平台](https://open.feishu.cn/)
- [飞书表格API文档](https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview)
- [飞书应用权限说明](https://open.feishu.cn/document/server-docs/permission/permission-overview)

## 支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 运行测试脚本检查配置
3. 查看飞书开放平台的应用日志
4. 提交issue到项目仓库