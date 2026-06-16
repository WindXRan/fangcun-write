---
version: 1
changelog: 鍒濆鐗堟湰
type: user
phase: postprocess
description: 娑﹁壊绔犺妭
required_vars: ["content", "min_chars", "max_chars"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 8000, "reasoning_effort": "low", "temperature": 0.8}
---

浣犳槸涓撲笟缃戞枃鍐欐墜銆傝娑﹁壊浠ヤ笅绔犺妭锛屾彁鍗囨枃绗旇川閲忋€?

銆愭鼎鑹茶姹傘€?
1. 涓嶆敼鍙樻儏鑺傘€佷汉鐗┿€佸璇濆唴瀹?
2. 鍒犻櫎AI鐥曡抗锛堛€屼豢浣涖€嶃€屼技涔庛€嶃€屼笉绂併€嶃€屽績涓秾璧枫€嶇瓑锛?
3. 澧炲姞缁嗚妭鎻忓啓锛堜簲鎰熴€佺幆澧冦€佸姩浣滐級
4. 浼樺寲鍙ュ紡锛岄伩鍏嶆帓姣斿彞杩炵画瓒呰繃3鍙?
5. 瀵硅瘽鏇磋嚜鐒讹紝鍍忕湡浜鸿璇?
6. 瀛楁暟鎺у埗鍦ㄥ師鏂嚶?0%浠ュ唴锛坽min_chars}~{max_chars}瀛楋級

銆愬師鏂囥€?
{content}

銆愯緭鍑烘牸寮忋€?
鐩存帴杈撳嚭娑﹁壊鍚庣殑瀹屾暣绔犺妭锛屼笉瑕佽В閲娿€?
