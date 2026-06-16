#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步配置管理
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

def backup_config():
    """备份配置"""
    print("💾 备份配置")
    print("=" * 50)
    
    backup_dir = Path(__file__).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = backup_dir / f"config_backup_{timestamp}"
    backup_subdir.mkdir(exist_ok=True)
    
    # 备份.env文件
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        shutil.copy2(env_file, backup_subdir / ".env")
        print(f"✅ 备份.env文件: {backup_subdir / '.env'}")
    else:
        print("⚠️  .env文件不存在，跳过备份")
    
    # 备份JSON配置文件
    config_file = Path(__file__).parent / "feishu_config.json"
    if config_file.exists():
        shutil.copy2(config_file, backup_subdir / "feishu_config.json")
        print(f"✅ 备份JSON配置文件: {backup_subdir / 'feishu_config.json'}")
    else:
        print("⚠️  JSON配置文件不存在，跳过备份")
    
    # 备份历史文件
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    if history_file.exists():
        shutil.copy2(history_file, backup_subdir / "feishu_sync_history.json")
        print(f"✅ 备份历史文件: {backup_subdir / 'feishu_sync_history.json'}")
    else:
        print("⚠️  历史文件不存在，跳过备份")
    
    # 创建备份信息文件
    backup_info = {
        "backup_time": timestamp,
        "backup_dir": str(backup_subdir),
        "files": []
    }
    
    for file in backup_subdir.glob("*"):
        backup_info["files"].append({
            "name": file.name,
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    with open(backup_subdir / "backup_info.json", 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 备份完成: {backup_subdir}")
    print(f"📁 备份文件数: {len(backup_info['files'])}")
    
    return True

def restore_config():
    """恢复配置"""
    print("🔄 恢复配置")
    print("=" * 50)
    
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        print("❌ 备份目录不存在")
        return False
    
    # 列出备份
    backups = sorted(backup_dir.glob("config_backup_*"), reverse=True)
    if not backups:
        print("❌ 没有找到备份")
        return False
    
    print("📋 可用的备份:")
    for i, backup in enumerate(backups, 1):
        backup_time = backup.name.replace("config_backup_", "")
        print(f"  {i}. {backup_time}")
    
    # 选择备份
    try:
        choice = int(input("\n请选择备份 (输入数字): ")) - 1
        if choice < 0 or choice >= len(backups):
            print("❌ 无效的选择")
            return False
    except ValueError:
        print("❌ 请输入有效的数字")
        return False
    
    selected_backup = backups[choice]
    print(f"\n选择的备份: {selected_backup.name}")
    
    # 显示备份信息
    backup_info_file = selected_backup / "backup_info.json"
    if backup_info_file.exists():
        with open(backup_info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
        
        print(f"备份时间: {backup_info.get('backup_time', '未知')}")
        print(f"备份文件数: {len(backup_info.get('files', []))}")
    
    # 确认恢复
    confirm = input("\n确认恢复？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消恢复")
        return False
    
    # 恢复.env文件
    env_backup = selected_backup / ".env"
    if env_backup.exists():
        shutil.copy2(env_backup, Path(__file__).parent / ".env")
        print("✅ 恢复.env文件")
    else:
        print("⚠️  备份中没有.env文件")
    
    # 恢复JSON配置文件
    config_backup = selected_backup / "feishu_config.json"
    if config_backup.exists():
        shutil.copy2(config_backup, Path(__file__).parent / "feishu_config.json")
        print("✅ 恢复JSON配置文件")
    else:
        print("⚠️  备份中没有JSON配置文件")
    
    # 恢复历史文件
    history_backup = selected_backup / "feishu_sync_history.json"
    if history_backup.exists():
        shutil.copy2(history_backup, Path(__file__).parent / "feishu_sync_history.json")
        print("✅ 恢复历史文件")
    else:
        print("⚠️  备份中没有历史文件")
    
    print(f"\n✅ 恢复完成")
    return True

def list_backups():
    """列出备份"""
    print("📋 备份列表")
    print("=" * 50)
    
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        print("❌ 备份目录不存在")
        return True
    
    backups = sorted(backup_dir.glob("config_backup_*"), reverse=True)
    if not backups:
        print("❌ 没有找到备份")
        return True
    
    print(f"📊 备份数量: {len(backups)}")
    print()
    
    for i, backup in enumerate(backups, 1):
        backup_time = backup.name.replace("config_backup_", "")
        print(f"{i}. {backup_time}")
        
        # 显示备份信息
        backup_info_file = backup / "backup_info.json"
        if backup_info_file.exists():
            with open(backup_info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
            
            print(f"   备份时间: {backup_info.get('backup_time', '未知')}")
            print(f"   备份文件数: {len(backup_info.get('files', []))}")
        
        # 列出备份内容
        files = list(backup.glob("*"))
        for file in files:
            if file.name != "backup_info.json":
                print(f"   - {file.name}")
        print()

def delete_backup():
    """删除备份"""
    print("🗑️  删除备份")
    print("=" * 50)
    
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        print("❌ 备份目录不存在")
        return True
    
    backups = sorted(backup_dir.glob("config_backup_*"), reverse=True)
    if not backups:
        print("❌ 没有找到备份")
        return True
    
    print("📋 可用的备份:")
    for i, backup in enumerate(backups, 1):
        backup_time = backup.name.replace("config_backup_", "")
        print(f"  {i}. {backup_time}")
    
    # 选择备份
    try:
        choice = int(input("\n请选择要删除的备份 (输入数字): ")) - 1
        if choice < 0 or choice >= len(backups):
            print("❌ 无效的选择")
            return False
    except ValueError:
        print("❌ 请输入有效的数字")
        return False
    
    selected_backup = backups[choice]
    print(f"\n选择的备份: {selected_backup.name}")
    
    # 确认删除
    confirm = input("确认删除？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消删除")
        return False
    
    # 删除备份
    try:
        shutil.rmtree(selected_backup)
        print(f"✅ 删除备份成功: {selected_backup.name}")
        return True
    except Exception as e:
        print(f"❌ 删除备份失败: {e}")
        return False

def export_config():
    """导出配置"""
    print("📤 导出配置")
    print("=" * 50)
    
    export_file = Path(__file__).parent / "feishu_config_export.json"
    
    # 收集配置
    config = {
        "export_time": datetime.now().isoformat(),
        "env_vars": {},
        "env_file": None,
        "json_config": None,
    }
    
    # 环境变量
    env_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            config["env_vars"][var] = value
    
    # .env文件
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            config["env_file"] = f.read()
    
    # JSON配置文件
    config_file = Path(__file__).parent / "feishu_config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config["json_config"] = json.load(f)
    
    # 写入导出文件
    with open(export_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置已导出: {export_file}")
    print(f"  大小: {export_file.stat().st_size} 字节")
    
    return True

def import_config():
    """导入配置"""
    print("📥 导入配置")
    print("=" * 50)
    
    import_file = Path(__file__).parent / "feishu_config_export.json"
    if not import_file.exists():
        print(f"❌ 导入文件不存在: {import_file}")
        return False
    
    try:
        with open(import_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ 读取导入文件成功")
        print(f"  导出时间: {config.get('export_time', '未知')}")
        
        # 导入环境变量
        if config.get("env_vars"):
            print("\n导入环境变量:")
            for var, value in config["env_vars"].items():
                os.environ[var] = value
                print(f"  ✅ {var}: 已设置")
        
        # 导入.env文件
        if config.get("env_file"):
            env_file = Path(__file__).parent / ".env"
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(config["env_file"])
            print(f"\n✅ 导入.env文件: {env_file}")
        
        # 导入JSON配置文件
        if config.get("json_config"):
            config_file = Path(__file__).parent / "feishu_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config["json_config"], f, indent=2, ensure_ascii=False)
            print(f"\n✅ 导入JSON配置文件: {config_file}")
        
        print("\n✅ 配置导入完成")
        return True
        
    except json.JSONDecodeError:
        print("❌ 导入文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 导入配置失败: {e}")
        return False

def reset_config():
    """重置配置"""
    print("🔄 重置配置")
    print("=" * 50)
    
    print("⚠️  警告：重置操作将删除所有配置文件！")
    confirm = input("确认重置？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消重置")
        return False
    
    # 删除.env文件
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        env_file.unlink()
        print("✅ 删除.env文件")
    
    # 删除JSON配置文件
    config_file = Path(__file__).parent / "feishu_config.json"
    if config_file.exists():
        config_file.unlink()
        print("✅ 删除JSON配置文件")
    
    # 删除历史文件
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    if history_file.exists():
        history_file.unlink()
        print("✅ 删除历史文件")
    
    print("\n✅ 配置重置完成")
    return True

def show_help():
    """显示帮助信息"""
    print("""
飞书同步配置管理

使用方法：
  python manage_config_feishu.py [选项]

选项：
  backup    备份配置
  restore   恢复配置
  list      列出备份
  delete    删除备份
  export    导出配置
  import    导入配置
  reset     重置配置
  help      显示帮助信息

示例：
  python manage_config_feishu.py backup   # 备份配置
  python manage_config_feishu.py restore  # 恢复配置
  python manage_config_feishu.py list     # 列出备份
  python manage_config_feishu.py export   # 导出配置
  python manage_config_feishu.py import   # 导入配置
  python manage_config_feishu.py reset    # 重置配置
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "backup":
        backup_config()
    elif command == "restore":
        restore_config()
    elif command == "list":
        list_backups()
    elif command == "delete":
        delete_backup()
    elif command == "export":
        export_config()
    elif command == "import":
        import_config()
    elif command == "reset":
        reset_config()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()