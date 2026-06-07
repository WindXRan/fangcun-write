"""创建仿写项目目录结构。"""
import sys, os

REWRITE_SUBDIRS = ['guides', 'chapters', 'compare', 'export']

def setup(count, project_dir):
    os.makedirs(project_dir, exist_ok=True)
    for sub in REWRITE_SUBDIRS:
        os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
    # 创建顶层设定文件空模板
    for name in ['concept.md', 'arc.md', 'truth.md']:
        path = os.path.join(project_dir, name)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write('')
    print(f"Created: {project_dir}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        count = int(sys.argv[2])
        project_dir = sys.argv[3]
        setup(count, project_dir)
    else:
        print("Usage: python create_templates.py setup <章节数> <项目目录>")
