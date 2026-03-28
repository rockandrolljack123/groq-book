import streamlit as st
from groq import Groq
import os
import re
import glob

st.title("IELTS Vocabulary Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

# ===== 词表 =====
def load_words():
    if not os.path.exists("ielts_words.txt"):
        return []
    with open("ielts_words.txt", "r", encoding="utf-8", errors="ignore") as f:
        return [w.strip() for w in f.readlines() if w.strip()]

# ===== 语料 + 文件来源 =====
def load_corpus():
    all_sentences = []

    # txt
    for file in sorted(glob.glob("cam*.txt")):
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                sentences = re.split(r'(?<=[.!?])\s+', text)
                for s in sentences:
                    s = s.strip()
                    if len(s) > 25:
                        all_sentences.append((s, file))
        except:
            pass

    # docx
    try:
        import docx
        for file in sorted(glob.glob("cam*.docx")):
            try:
                doc = docx.Document(file)
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                sentences = re.split(r'(?<=[.!?])\s+', text)
                for s in sentences:
                    s = s.strip()
                    if len(s) > 25:
                        all_sentences.append((s, file))
            except:
                pass
    except:
        pass

    return all_sentences

all_sentences = load_corpus()

# ===== 查句子（返回句子+来源）=====
def find_sentence(word):
    word = word.strip()
    if not word:
        return None, None

    # phrase
    if " " in word or "-" in word:
        for s, f in all_sentences:
            if word.lower() in s.lower():
                return s, f

    # exact
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for s, f in all_sentences:
        if pattern.search(s):
            return s, f

    # variants
    variants = [
        word,
        word + "s",
        word + "ed",
        word + "ing",
        word[:-1] + "ing" if word.endswith("e") else word + "ing"
    ]

    for v in variants:
        pattern_v = re.compile(rf"\b{re.escape(v)}\b", re.IGNORECASE)
        for s, f in all_sentences:
            if pattern_v.search(s):
                return s, f

    return None, None

# ===== AI补充 =====
def enrich(word, sentence):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "你是雅思词汇书作者，简洁输出"},
            {"role": "user", "content": f"""
词：{word}

例句：{sentence if sentence else "无"}

输出：
IPA:
中文解释:
例句翻译:
同义词(2个):
"""}
        ]
    )
    return response.choices[0].message.content

# ===== UI =====
words = load_words()

st.write(f"词表数量: {len(words)}")
st.write(f"语料句子数: {len(all_sentences)}")

if st.button("Generate"):
    found = 0

    for i, word in enumerate(words[:50], 1):
        st.markdown(f"## {i}. {word}")

        sentence, source = find_sentence(word)

        if sentence:
            found += 1
            st.write(sentence)
            st.write(f"来源: {source}")
        else:
            st.write("⚠️ 未找到例句")

        st.write(enrich(word, sentence))
        st.markdown("---")

    st.success(f"匹配成功: {found}/50")
