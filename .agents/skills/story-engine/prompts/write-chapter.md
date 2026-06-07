写《{新书名}》第{N}章。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
【style_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/style_{N}.md

第一步：读上面两个文件，找到"新书目标字数"。
第二步：按plot_guide的节拍表写正文，每个节拍按分配的字数写。
第三步：写入文件。
第四步：运行 powershell -ExecutionPolicy Bypass -File ".agents/hooks/count-words.ps1" "projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt" {目标字数} 200

⚠️ 禁止逐句检查字数、禁止反复修改、禁止输出任何分析过程。

输出到：projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
