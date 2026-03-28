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

# ===== 读取词表 =====
def load_words():
    if not os.path.exists("ielts_words.txt"):
        return []
    with open("ielts_words.txt", "r", encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.readlines() if w.strip()]
    return words

# ===== 读取所有 cam 文件（不再写死文件名）=====
def load_corpus():
    loaded_files = []
    text_parts = []

    # 读取所有 txt
    for file in sorted(glob.glob("cam*.txt")):
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    text_parts.append(content)
                    loaded_files.append(file)
        except Exception:
            pass

    # 读取所有 docx
    try:
        import docx
        for file in sorted(glob.glob("cam*.docx")):
            try:
                doc = docx.Document(file)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                content = "\n".join(paras)
                if content.strip():
                    text_parts.append(content)
                    loaded_files.append(file)
            except Exception:
                pass
    except Exception:
        pass

    corpus_text = "\n".join(text_parts)
    corpus_text = re.sub(r"\s+", " ", corpus_text).strip()
    return corpus_text, loaded_files

corpus, loaded_files = load_corpus()

# ===== 切句（更稳）=====
def split_sentences(text):
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+', text)
    clean_parts = []
    for p in parts:
        p = p.strip()
        if len(p) >= 25:
            clean_parts.append(p)
    return clean_parts

sentences = split_sentences(corpus)

# ===== 更稳的例句检索 =====
def find_sentence(word):
    word = word.strip()
    if not word:
        return None

    # 如果是词组，直接宽松匹配
    if " " in word or "-" in word:
        low_word = word.lower()
        for s in sentences:
            if low_word in s.lower():
                return s
        return None

    # 如果是单个词，先做严格匹配
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for s in sentences:
        if pattern.search(s):
            return s

    # 再做常见词形变化匹配
    variants = [
        word,
        word + "s",
        word + "ed",
        word + "ing",
        word[:-1] + "ing" if word.endswith("e") else word + "ing",
        word + "ly",
        word + "al",
        word + "ion",
        word + "ment",
    ]

    for v in variants:
        pattern_v = re.compile(rf"\b{re.escape(v)}\b", re.IGNORECASE)
        for s in sentences:
            if pattern_v.search(s):
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
st.write(f"已加载语料文件: {', '.join(loaded_files) if loaded_files else '无'}")
st.write(f"语料句子数量: {len(sentences)}")

if st.button("Generate"):
    if not words:
        st.error("没有词表")
    elif not sentences:
        st.error("没有成功加载剑桥语料，请先检查 cam 文件是否已上传")
    else:
        found_count = 0

        for i, word in enumerate(words[:50], 1):
            st.markdown(f"## {i}. {word}")

            sentence = find_sentence(word)

            if sentence:
                found_count += 1
                st.write(f"例句（Cambridge）: {sentence}")
                st.write("来源: Cambridge 16–20（自动匹配）")
            else:
                st.write("⚠️ 未找到例句")

            info = enrich(word, sentence)
            st.write(info)

            st.markdown("---")

        st.success(f"本次 50 个词中，成功匹配到 {found_count} 个例句。")
