写《{新书名}》第{N}章。

【plot_guide】仿写/{新书名}_仿写/设定/guides/plot_guide_{N}.md
【style_guide】仿写/{新书名}_仿写/设定/guides/style_guide_{N}.md

第一步：读上面两个文件，找到"新书目标字数"。
第二步：按plot_guide的节拍表写正文，每个节拍按分配的字数写。
第三步：写入文件。
第四步：运行 powershell -ExecutionPolicy Bypass -File ".agents/hooks/count-words.ps1" "仿写/{新书名}_仿写/正文/第{N}章.txt" {目标字数} 200

⚠️ 禁止逐句检查字数、禁止反复修改、禁止输出任何分析过程。

输出到：仿写/{新书名}_仿写/正文/第{N}章.txt
