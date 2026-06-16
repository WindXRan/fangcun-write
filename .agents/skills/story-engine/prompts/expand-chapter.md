---
version: 1
changelog: 鍒濆鐗堟湰
type: user
phase: postprocess
description: 鎵╁啓绔犺妭
required_vars: ["content", "orig_chars", "target_chars", "min_chars", "max_chars"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 10000, "reasoning_effort": "low", "temperature": 0.8}
---

浣犳槸涓撲笟缃戞枃鍐欐墜銆傝鎵╁啓浠ヤ笅绔犺妭锛屽鍔犲唴瀹逛娇瀛楁暟杈惧埌{target_chars}瀛楀乏鍙炽€?

銆愭墿鍐欒姹傘€?
1. 淇濇寔鍘熸湁鎯呰妭妗嗘灦鍜屼汉鐗╁叧绯?
2. 澧炲姞缁嗚妭鎻忓啓锛堢幆澧冦€佸績鐞嗐€佸姩浣滐級
3. 澧炲姞瀵硅瘽浜掑姩
4. 澧炲姞鍦烘櫙杩囨浮
5. 涓嶈澧炲姞鏂扮殑鎯呰妭绾?
6. 瀛楁暟鎺у埗鍦▄min_chars}~{max_chars}瀛?

銆愬師鏂囷紙{orig_chars}瀛楋級銆?
{content}

銆愯緭鍑烘牸寮忋€?
鐩存帴杈撳嚭鎵╁啓鍚庣殑瀹屾暣绔犺妭锛屼笉瑕佽В閲娿€?
