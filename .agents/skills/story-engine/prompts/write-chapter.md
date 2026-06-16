---
version: 9
changelog: 鏋佽嚧绮剧畝鈥斺€旈鏍肩敱plot_guide寮曞锛岃川閲忕敱unified_review鍏滃簳锛寃rite鍙礋璐ｅ垱浣?type: user
phase: write
description: 鍐欑珷
required_vars: ["N", "鏂颁功鍚?, "浣滆€呭悕", "婧愪功鍚?, "鐩爣瀛楁暟", "鐩爣瀛楁暟_min", "鐩爣瀛楁暟_max"]
optional_vars: ["濂充富鍚?, "鐢蜂富鍚?]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 8192, "reasoning_effort": "high", "temperature": 0.8}
---

鍐欍€妠鏂颁功鍚峿銆嬬{N}绔犮€?
銆恜lot_guide銆憄rojects/{浣滆€呭悕}/{婧愪功鍚峿/rewrites/{鏂颁功鍚峿/guides/plot_{N}.md
銆愭簮鏂囧叏鏂囥€憄rojects/{浣滆€呭悕}/{婧愪功鍚峿/_cache/chapters/绗瑊N}绔?txt
銆愭枃绗旀寚绾广€憄rojects/{浣滆€呭悕}/{婧愪功鍚峿/_cache/styles/style_{N:03d}.md

鎸?plot_guide 鐨勫彊浜嬬瓥鐣ュ拰鑺傛媿鍒涗綔銆傜珷鍚嶅彇 plot_guide 鏍囨敞鐨勶紝鏈爣娉ㄥ垯鑷嫙銆傛鏂囩涓€琛屽啓"绗瑊N}绔?[绔犲悕]"锛堜笉鍔?锛夈€?
鏂囩瑪鎸囩汗鏄簮鏂囩殑椋庢牸閿氱偣锛屼豢鍐欐椂蹇呴』瀵规爣锛氬彞闀裤€佸璇濇瘮渚嬨€佹钀介暱搴︺€佷唬璇嶅瘑搴︾瓑鎸囨爣瑕佷笌婧愭枃涓€鑷淬€?
瀛楁暟锛歿鐩爣瀛楁暟}瀛楋紙{鐩爣瀛楁暟_min}~{鐩爣瀛楁暟_max}锛夈€?
瑙掕壊锛氬コ涓?{濂充富鍚峿锛岀敺涓?{鐢蜂富鍚峿銆?
杈撳嚭锛歱rojects/{浣滆€呭悕}/{婧愪功鍚峿/rewrites/{鏂颁功鍚峿/chapters/ch_{N}.txt
