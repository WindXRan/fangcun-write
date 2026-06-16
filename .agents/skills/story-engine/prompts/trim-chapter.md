---
version: 1
changelog: 鍒濆鐗堟湰
type: user
phase: postprocess
description: 绮剧畝瓒呭瓧鏁扮珷
required_vars: ["鐩爣瀛楁暟", "浣滆€呭悕", "婧愪功鍚?, "鏂颁功鍚?, "N", "N03d"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 4096, "reasoning_effort": "high", "temperature": 0.8}
---

绮剧畝浠ヤ笅绔犺妭锛岀洰鏍?{鐩爣瀛楁暟} 瀛椼€?

銆愬師鏂囥€憄rojects/{浣滆€呭悕}/{婧愪功鍚峿/rewrites/{鏂颁功鍚峿/chapters/ch_{N03d}.txt

---

## 瑙勫垯

1. **淇濈暀鎵€鏈夊墽鎯呰妭鐐瑰拰鍏抽敭瀵硅瘽**锛屼竴涓兘涓嶈兘涓?
2. **鍒犲啑浣?*锛氶噸澶嶆弿鍐欍€佽繃搴︿慨楗般€佸彲鏈夊彲鏃犵殑鍓瘝锛堝井寰?杞昏交/娣℃贰/缂撶紦锛?
3. **鍚堢煭鍙?*锛氳繛缁殑 2-3 涓瀬鐭彞濡傛灉琛ㄨ揪鍚屼竴浠朵簨锛屽悎骞?
4. **鐮嶅簾璇?*锛氳鑹插唴蹇冪嫭鐧藉鏋滃凡缁忕敤鍔ㄤ綔琛ㄨ揪杩囦簡锛屽垹鎺夌嫭鐧?
5. 杈撳嚭绮剧畝鍚庣殑鍏ㄦ枃锛屼笉瑕佸垎鏋愯繃绋?

杈撳嚭鍒帮細projects/{浣滆€呭悕}/{婧愪功鍚峿/rewrites/{鏂颁功鍚峿/chapters/ch_{N}.txt

銆愯緭鍑恒€憄rojects/{浣滆€呭悕}/{婧愪功鍚峿/rewrites/{鏂颁功鍚峿/chapters/ch_{N}.txt
