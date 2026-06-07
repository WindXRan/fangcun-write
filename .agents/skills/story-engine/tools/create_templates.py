"""创建仿写项目目录结构。"""
import sys, os

def setup(count, project_dir):
    os.makedirs(project_dir, exist_ok=True)
    for sub in ['设定', '设定/guides', '追踪', '正文']:
        os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
    print(f"Created: {project_dir}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        count = int(sys.argv[2])
        project_dir = sys.argv[3]
        setup(count, project_dir)
    else:
        print("Usage: python create_templates.py setup <章节数> <项目目录>")
