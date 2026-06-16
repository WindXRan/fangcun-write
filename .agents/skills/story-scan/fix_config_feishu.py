#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复飞书同步配置
"""

import os
import sys
import json
import shutil
from pathlib import Path

def fix_env_file():
    """修复.env文件"""
    print("🔧 修复.env文件")
    print("=" * 50)
    
    env_file = Path(__file__).parent / ".env"
    env_example = Path(__file__).parent / ".env.example"
    
    # 检查.env文件是否存在
    if not env_file.exists():
        print("❌ .env文件不存在")
        
        # 检查是否有.env.example文件
        if env_example.exists():
            print("📋 找到.env.example文件")
            choice = input("是否从.env.example创建.env文件？(y/N): ").strip().lower()
            if choice == 'y':
                shutil.copy2(env_example, env_file)
                print(f"✅ 已从.env.example创建.env文件: {env_file}")
                print("请编辑.env文件，填入正确的飞书配置")
                return True
            else:
                print("❌ 取消创建.env文件")
                return False
        else:
            print("❌ 没有找到.env.example文件")
            print("   解决方案: 手动创建.env文件")
            return False
    
    print(f"✅ .env文件存在: {env_file}")
    
    # 检查文件内容
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
        missing_vars = []
        
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少变量: {', '.join(missing_vars)}")
            print("   解决方案: 在.env文件中添加缺少的变量")
            
            choice = input("是否自动添加缺少的变量？(y/N): ").strip().lower()
            if choice == 'y':
                with open(env_file, 'a', encoding='utf-8') as f:
                    f.write("\n# 飞书配置\n")
                    for var in missing_vars:
                        f.write(f"{var}=your-{var.lower().replace('_', '-')}\n")
                print(f"✅ 已添加缺少的变量到.env文件")
                print("请编辑.env文件，填入正确的值")
                return True
            else:
                print("❌ 取消添加变量")
                return False
        
        print("✅ .env文件内容完整")
        return True
        
    except Exception as e:
        print(f"❌ 读取.env文件失败: {e}")
        return False

def fix_json_config():
    """修复JSON配置文件"""
    print("\n🔧 修复JSON配置文件")
    print("=" * 50)
    
    config_file = Path(__file__).parent / "feishu_config.json"
    
    # 检查配置文件是否存在
    if not config_file.exists():
        print("❌ JSON配置文件不存在")
        
        choice = input("是否创建JSON配置文件？(y/N): ").strip().lower()
        if choice == 'y':
            config = {
                "feishu": {
                    "app_id": "your-app-id",
                    "app_secret": "your-app-secret",
                    "spreadsheet_token": "your-spreadsheet-token",
                    "sheet_id": "your-sheet-id"
                },
                "sync": {
                    "auto_sync": False,
                    "sync_interval": 3600,
                    "data_types": ["ranks", "summary", "market_data"]
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已创建JSON配置文件: {config_file}")
            print("请编辑配置文件，填入正确的飞书配置")
            return True
        else:
            print("❌ 取消创建JSON配置文件")
            return False
    
    print(f"✅ JSON配置文件存在: {config_file}")
    
    # 检查文件内容
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        feishu_config = config.get('feishu', {})
        if not feishu_config:
            print("❌ 飞书配置为空")
            
            choice = input("是否添加飞书配置？(y/N): ").strip().lower()
            if choice == 'y':
                config['feishu'] = {
                    "app_id": "your-app-id",
                    "app_secret": "your-app-secret",
                    "spreadsheet_token": "your-spreadsheet-token",
                    "sheet_id": "your-sheet-id"
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                print("✅ 已添加飞书配置")
                print("请编辑配置文件，填入正确的值")
                return True
            else:
                print("❌ 取消添加飞书配置")
                return False
        
        required_keys = ['app_id', 'app_secret', 'spreadsheet_token', 'sheet_id']
        missing_keys = [key for key in required_keys if key not in feishu_config]
        
        if missing_keys:
            print(f"❌ 缺少配置项: {', '.join(missing_keys)}")
            
            choice = input("是否添加缺少的配置项？(y/N): ").strip().lower()
            if choice == 'y':
                for key in missing_keys:
                    feishu_config[key] = f"your-{key.replace('_', '-')}"
                
                config['feishu'] = feishu_config
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                print("✅ 已添加缺少的配置项")
                print("请编辑配置文件，填入正确的值")
                return True
            else:
                print("❌ 取消添加配置项")
                return False
        
        print("✅ JSON配置文件内容完整")
        return True
        
    except json.JSONDecodeError:
        print("❌ JSON配置文件格式错误")
        
        choice = input("是否重新创建JSON配置文件？(y/N): ").strip().lower()
        if choice == 'y':
            config = {
                "feishu": {
                    "app_id": "your-app-id",
                    "app_secret": "your-app-secret",
                    "spreadsheet_token": "your-spreadsheet-token",
                    "sheet_id": "your-sheet-id"
                },
                "sync": {
                    "auto_sync": False,
                    "sync_interval": 3600,
                    "data_types": ["ranks", "summary", "market_data"]
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已重新创建JSON配置文件: {config_file}")
            print("请编辑配置文件，填入正确的飞书配置")
            return True
        else:
            print("❌ 取消重新创建JSON配置文件")
            return False
    except Exception as e:
        print(f"❌ 读取JSON配置文件失败: {e}")
        return False

def fix_data_files():
    """修复数据文件"""
    print("\n🔧 修复数据文件")
    print("=" * 50)
    
    data_dir = Path(__file__).parent / "data"
    
    # 检查数据目录
    if not data_dir.exists():
        print("❌ 数据目录不存在")
        
        choice = input("是否创建数据目录？(y/N): ").strip().lower()
        if choice == 'y':
            data_dir.mkdir(exist_ok=True)
            print(f"✅ 已创建数据目录: {data_dir}")
        else:
            print("❌ 取消创建数据目录")
            return False
    
    print(f"✅ 数据目录存在: {data_dir}")
    
    # 检查排行榜数据
    rank_files = list(data_dir.glob("latest_*_ranks.json"))
    if not rank_files:
        print("❌ 排行榜数据: 无")
        
        choice = input("是否运行数据采集脚本？(y/N): ").strip().lower()
        if choice == 'y':
            print("请运行以下命令采集数据:")
            print("  python run.py scrape")
            print("  python run.py build")
            return False
        else:
            print("❌ 取消数据采集")
            return False
    
    print(f"✅ 排行榜数据: {len(rank_files)} 个文件")
    
    # 检查市场总结
    summary_files = list(data_dir.glob("market_summary_*.json"))
    if not summary_files:
        print("❌ 市场总结: 无")
        
        choice = input("是否运行数据构建脚本？(y/N): ").strip().lower()
        if choice == 'y':
            print("请运行以下命令构建数据:")
            print("  python run.py build")
            return False
        else:
            print("❌ 取消数据构建")
            return False
    
    print(f"✅ 市场总结: {len(summary_files)} 个文件")
    
    # 检查市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if not market_data_file.exists():
        print("❌ 市场数据: 无")
        
        choice = input("是否运行市场数据同步脚本？(y/N): ").strip().lower()
        if choice == 'y':
            print("请运行以下命令同步市场数据:")
            print("  python sync_market_data.py")
            return False
        else:
            print("❌ 取消市场数据同步")
            return False
    
    print(f"✅ 市场数据: {market_data_file.name}")
    
    print("✅ 数据文件检查通过")
    return True

def fix_dependencies():
    """修复依赖"""
    print("\n🔧 修复依赖")
    print("=" * 50)
    
    try:
        import requests
        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests: 未安装")
        
        choice = input("是否安装requests库？(y/N): ").strip().lower()
        if choice == 'y':
            import subprocess
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
                print("✅ requests安装成功")
                return True
            except subprocess.CalledProcessError:
                print("❌ requests安装失败")
                print("请手动运行: pip install requests")
                return False
        else:
            print("❌ 取消安装requests")
            return False
    
    print("✅ 依赖检查通过")
    return True

def fix_all():
    """修复所有配置"""
    print("🔧 飞书同步配置完整修复")
    print("=" * 50)
    print()
    
    fixes = [
        ("环境文件", fix_env_file),
        ("JSON配置文件", fix_json_config),
        ("数据文件", fix_data_files),
        ("依赖", fix_dependencies),
    ]
    
    results = []
    all_passed = True
    
    for name, fix_func in fixes:
        try:
            ok = fix_func()
            results.append((name, ok))
            if not ok:
                all_passed = False
        except Exception as e:
            results.append((name, False))
            all_passed = False
    
    # 显示修复结果
    print("\n📋 修复结果")
    print("=" * 50)
    
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有修复完成！")
        print("\n下一步:")
        print("  1. 编辑配置文件，填入正确的飞书配置")
        print("  2. 运行 'python test_feishu_sync.py' 测试配置")
        print("  3. 运行 'python feishu_sync.py' 同步数据")
    else:
        print("❌ 部分修复失败")
        print("\n请根据上述提示手动修复")
        print("查看帮助: python help_feishu.py")
    
    return all_passed

def show_help():
    """显示帮助信息"""
    print("""
修复飞书同步配置

使用方法：
  python fix_config_feishu.py [选项]

选项：
  env         修复.env文件
  json        修复JSON配置文件
  data        修复数据文件
  deps        修复依赖
  all         修复所有配置
  help        显示帮助信息

示例：
  python fix_config_feishu.py env    # 修复.env文件
  python fix_config_feishu.py json   # 修复JSON配置文件
  python fix_config_feishu.py all    # 修复所有配置
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        fix_env_file()
    elif command == "json":
        fix_json_config()
    elif command == "data":
        fix_data_files()
    elif command == "deps":
        fix_dependencies()
    elif command == "all":
        fix_all()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()