# Reviser锛氳嚜鍔ㄤ慨璁?
**LLM 椹卞姩銆傝鍙栧璁℃姤鍛?+ 鍘熸枃锛岃緭鍑轰慨璁㈢増銆?*

---

## 瑙﹀彂鏂瑰紡

瀹¤ failed 鏃惰嚜鍔ㄨЕ鍙戯紝鎴栨墜鍔?`/revise`

---

## 淇 prompt 妯℃澘

```
浣犳槸淇鑰呫€傛牴鎹璁℃姤鍛婁慨璁㈢珷鑺傛鏂囥€?
## 鍘熸枃
{original_chapter}

## 瀹¤鎶ュ憡
{audit_report}

## Truth Files锛堜慨璁㈠悗蹇呴』淇濇寔涓€鑷达級
{truth_files_summary}

## 淇瑙勫垯

1. 鍙慨澶嶅璁℃姤鍛婁腑鏍囪涓?critical 鍜?warning 鐨?issue
2. info 绾у埆鐨?issue 鍙€夋嫨鎬т慨澶?3. 淇鍚庣殑鍐呭蹇呴』涓?truth files 淇濇寔涓€鑷?4. 涓嶈兘寮曞叆鏂扮殑 OOC銆佹椂闂寸嚎鐭涚浘銆佽瀹氬啿绐?5. 淇濇寔鍘熸枃鐨勫瓧鏁拌寖鍥达紙卤20%锛?6. 淇濇寔鍘熸枃鐨勬儏缁熀璋冨拰鑺傚
7. 淇濈暀鍘熸枃鐨勪紡绗旈摵璁?
## 杈撳嚭鏍煎紡

杈撳嚭淇鍚庣殑瀹屾暣绔犺妭姝ｆ枃锛岀洿鎺ュ啓鍏ユ枃浠躲€?
## 淇妯″紡

| 妯″紡 | 璇存槑 | 閫傜敤鍦烘櫙 |
|------|------|---------|
| spot-fix | 瀹氱偣淇锛屽彧鏀规湁闂鐨勬钀?| issue 鈮? 涓紝涓旈兘鏄眬閮ㄩ棶棰?|
| rewrite | 閲嶅啓鏁翠釜绔犺妭 | issue >3 涓紝鎴栨湁缁撴瀯鎬ч棶棰?|
| anti-detect | 鍙嶆娴嬩慨璁?| AI 鐥曡抗杩囬噸鏃?|

榛樿浣跨敤 spot-fix銆俰ssue >3 涓椂鑷姩鍗囩骇涓?rewrite銆?```

---

## 淇鍚庢祦绋?
```
淇瀹屾垚
鈹溾攢鈹€ 閲嶈窇 post_write_validator.py锛堥浂 LLM锛?鈹?  鈹溾攢鈹€ error 鈫?鍐嶄慨璁竴娆?鈹?  鈹斺攢鈹€ pass 鈫?鈶?鈹溾攢鈹€ 閲嶈窇 auditor锛圠LM锛?鈹?  鈹溾攢鈹€ passed 鈫?閫氳繃
鈹?  鈹斺攢鈹€ failed 鈫?鏍囪 manual_required锛屼笉鍐嶈嚜鍔ㄤ慨璁?鈹斺攢鈹€ 鏇存柊 truth files锛圤bserver锛?```

---

## 淇娆℃暟闄愬埗

- 姣忕珷鏈€澶氳嚜鍔ㄤ慨璁?**1 娆?*
- 淇鍚庝粛 failed 鈫?鏍囪 `manual_required`
- 杩炵画 3 绔?manual_required 鈫?鏆傚仠锛岀瓑寰呬汉宸ヤ粙鍏?
---

## 涓?rewrite 闆嗘垚

鍦?story-rewrite 鐨?Step 4 鏍￠獙涓細

```
Step 4锛氭牎楠?  鈶?post_write_validator.py锛堥浂 LLM锛?     error 鈫?鐩存帴閲嶅啓锛堜笉璧颁慨璁紝鐩存帴閲嶅啓鏁寸珷锛?     pass 鈫?鈶?  鈶?auditor锛圠LM锛?3 缁达級
     passed 鈫?閫氳繃
     failed 鈫?鈶?  鈶?reviser锛圠LM锛岃嚜鍔ㄤ慨璁級
     spot-fix/rewrite 鈫?鈶?  鈶?閲嶈窇 auditor
     passed 鈫?閫氳繃
     failed 鈫?manual_required
```
