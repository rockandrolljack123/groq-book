import streamlit as st
from groq import Groq
import os
import re

st.title("AI Book Generator (Cambridge Version)")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

# ========= 读取语料 =========
def load_text_files():
    texts = []
    for file in ["cam16.txt", "cam17.txt"]:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                texts.append(f.read())
    return "\n".join(texts)

def load_docx_files():
    try:
        import docx
    except:
        return ""
    texts = []
    for file in ["cam18.docx", "cam19.docx", "cam20.docx"]:
        if os.path.exists(file):
            doc = docx.Document(file)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            texts.append("\n".join(full_text))
    return "\n".join(texts)

corpus = load_text_files() + "\n" + load_docx_files()

# ========= 简单句子切分 =========
sentences = re.split(r"[.!?]", corpus)

def find_sentence(word):
    for s in sentences:
        if word.lower() in s.lower() and len(s.strip()) > 20:
            return s.strip()
    return None

# ========= UI =========
topic = st.text_input("Enter topic (e.g. transportation):")

if st.button("Generate"):
    if not topic:
        st.warning("Enter a topic")
    else:
        try:
            # 先生成词汇列表
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
请生成与“{topic}”相关的50个雅思核心词汇（只要单词列表，不要解释）
"""
                    }
                ]
            )

            words_text = response.choices[0].message.content
            words = re.findall(r"[a-zA-Z]+", words_text)

            words = list(dict.fromkeys(words))[:50]

            st.success(f"生成 {len(words)} 个词")

            for i, word in enumerate(words, 1):
                st.markdown(f"## {i}. {word}")

                sentence = find_sentence(word)

                if sentence:
                    st.write(f"**例句（剑桥）**: {sentence}")
                else:
                    st.write("⚠️ 未在剑桥语料中找到例句")

                # 再让AI补其他信息
                response2 = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "user",
                            "content": f"""
给这个单词补充信息：

{word}

输出：
- IPA
- 中文解释
- 中文翻译（针对例句）
- 2个同义词
"""
                        }
                    ]
                )

                st.write(response2.choices[0].message.content)
                st.markdown("---")

        except Exception as e:
            st.error(str(e))
