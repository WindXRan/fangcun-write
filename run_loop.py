"""运行 loop engine 自动迭代"""
import sys, os
sys.path.insert(0, '.agents/skills/story-engine/tools')
base = os.path.dirname(os.path.abspath(__file__))
os.environ['API_KEY'] = 'sk-ad9450b1670b485c8a456a52520dc5a8'

from loop_engine import run_loop

config_path = os.path.join(base, 'configs/test_new_plot.json')

# 检查 config 是否存在
if not os.path.exists(config_path):
    print(f"Config not found: {config_path}")
    print("Creating inline config...")
    import json
    config = {
        "book_name": "斗破苍穹之星辰再起",
        "author": "天蚕土豆",
        "source_book": "斗破苍穹",
        "api_key": os.environ['API_KEY'],
        "model": "deepseek-v4-pro",
        "prompts_dir": ".agents/skills/story-engine/prompts",
        "rewrites_dir": "projects/天蚕土豆/斗破苍穹/rewrites/斗破苍穹之星辰再起",
        "base_dir": base,
    }
    config_path = os.path.join(base, 'configs', '_loop_test.json')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# 跑 3 轮, 第 1-3 章
history = run_loop(config_path, start=1, end=3, max_loops=3, auto_apply=False)
print("\nDONE")
