import streamlit as st
from groq import Groq
import json

st.title("AI Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

topic = st.text_input("Enter your book topic:")

SYSTEM_PROMPT = """
你是一名出版级英语词汇书作者。
你必须严格按要求输出 JSON，不要输出任何解释、前言、总结、代码块标记。
"""

def build_user_prompt(topic_text: str, existing_words: list[str] | None = None) -> str:
    existing_words = existing_words or []
    exclude_text = "、".join(existing_words) if existing_words else "无"

    return f"""
任务：围绕【{topic_text}】生成雅思核心词汇书内容。

硬性要求：
1. 总共必须完成 50 个不同的词或词组。
2. 这一次请尽可能多生成，至少生成 20 个；如果无法一次完成，也必须输出有效 JSON。
3. 不能与以下已生成词重复：{exclude_text}
4. 每个词必须包含以下字段：
   - word
   - ipa
   - meaning_cn
   - example_en
   - example_cn
   - synonyms（数组，2-3个）
5. 内容必须适合中国雅思学习者，中文解释简洁，英文例句自然。
6. 只输出 JSON，格式如下：

{{
  "items": [
    {{
      "word": "commute",
      "ipa": "/kəˈmjuːt/",
      "meaning_cn": "通勤",
      "example_en": "My daily commute takes about an hour.",
      "example_cn": "我每天通勤大约要一个小时。",
      "synonyms": ["travel to work", "journey to work", "go to work"]
    }}
  ],
  "done": false
}}

说明：
- 如果你认为 50 个已经全部完成，则 done 写 true
- 如果还没完成，则 done 写 false
- 不要输出 markdown，不要输出 ```json
"""

def call_model(user_prompt: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=6000,
    )

    text = response.choices[0].message.content.strip()
    return json.loads(text)

if st.button("Generate Book"):
    if not topic.strip():
        st.warning("Please enter a topic")
    else:
        try:
            all_items = []
            seen_words = set()

            for _ in range(5):
                data = call_model(build_user_prompt(topic, list(seen_words)))
                items = data.get("items", [])

                for item in items:
                    word = item.get("word", "").strip()
                    if word and word.lower() not in seen_words:
                        seen_words.add(word.lower())
                        all_items.append(item)

                if len(all_items) >= 50:
                    break

                if data.get("done") is True:
                    break

            all_items = all_items[:50]

            if len(all_items) < 50:
                st.error(f"只生成了 {len(all_items)} 个词，还没达到 50 个。")
            else:
                st.success("已生成 50 个词。")

            for idx, item in enumerate(all_items, start=1):
                st.markdown(f"## {idx}. {item.get('word', '')}")
                st.write(f"**英式音标（IPA）**: {item.get('ipa', '')}")
                st.write(f"**中文核心释义**: {item.get('meaning_cn', '')}")
                st.write(f"**英文例句**: {item.get('example_en', '')}")
                st.write(f"**中文翻译**: {item.get('example_cn', '')}")
                synonyms = item.get("synonyms", [])
                if isinstance(synonyms, list):
                    st.write(f"**同义替换**: {', '.join(synonyms)}")
                else:
                    st.write(f"**同义替换**: {synonyms}")
                st.write("👉 扫码，用这个词完成一轮AI测试")
                st.markdown("---")

        except Exception as e:
            st.error(str(e))
