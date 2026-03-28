import streamlit as st
from groq import Groq
import os
import re

st.title("IELTS Vocabulary Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

# ===== 读取词表 =====
def load_words():
    if not os.path.exists("ielts_words.txt"):
        return []
    with open("ielts_words.txt", "r", encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.readlines() if w.strip()]
    return words

# ===== 读取语料 =====
def load_corpus():
    text = ""

    for file in ["cam16.txt", "cam17.txt"]:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                text += f.read() + "\n"

    try:
        import docx
        for file in ["cam18.docx", "cam19.docx", "cam20.docx"]:
            if os.path.exists(file):
                doc = docx.Document(file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
    except:
        pass

    return text

corpus = load_corpus()
sentences = re.split(r"(?<=[.!?])\s+", corpus)

def find_sentence(word):
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and pattern.search(s):
            return s
    return None

# ===== AI补充信息 =====
def enrich(word, sentence):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "你是雅思词汇书作者。只输出简洁内容，不要解释。"
            },
            {
                "role": "user",
                "content": f"""
给这个词补充信息：

{word}

例句：
{sentence if sentence else "无"}

输出：
IPA:
中文解释:
例句翻译:
同义词(2个):
"""
            }
        ]
    )

    return response.choices[0].message.content

# ===== UI =====
words = load_words()

st.write(f"当前词表数量: {len(words)}")

if st.button("Generate"):
    if not words:
        st.error("没有词表")
    else:
        for i, word in enumerate(words[:50], 1):

            st.markdown(f"## {i}. {word}")

            sentence = find_sentence(word)

            if sentence:
                st.write(f"例句（Cambridge）: {sentence}")
                st.write("来源: Cambridge 16–20（自动匹配）")
            else:
                st.write("⚠️ 未找到例句")

            info = enrich(word, sentence)
            st.write(info)

            st.markdown("---")
