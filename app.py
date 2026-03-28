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
        return [w.strip() for w in f.readlines() if w.strip()]

# ===== 来源格式化 =====
def format_file_label(filename):
    m = re.search(r"cam(\d+)", filename.lower())
    if m:
        return f"IELTS {m.group(1)}"
    return filename

# ===== 从文本中追踪 Test / Passage 标签 =====
def parse_text_with_labels(text, filename):
    lines = text.splitlines()
    results = []

    current_test = ""
    current_passage = ""

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        # 更新 Test 标签
        m_test = re.search(r"\bTest\s*(\d+)\b", raw, re.IGNORECASE)
        if m_test:
            current_test = f"Test {m_test.group(1)}"

        # 更新 Reading Passage 标签
        m_passage = re.search(r"\bReading\s*Passage\s*(\d+)\b", raw, re.IGNORECASE)
        if m_passage:
            current_passage = f"Reading Passage {m_passage.group(1)}"

        # 把当前行切成句子
        parts = re.split(r'(?<=[.!?])\s+', raw)
        for p in parts:
            p = p.strip()
            if len(p) >= 25:
                source_parts = [format_file_label(filename)]
                if current_test:
                    source_parts.append(current_test)
                if current_passage:
                    source_parts.append(current_passage)

                source = "_".join(source_parts)
                results.append(
                    {
                        "sentence": p,
                        "source": source
                    }
                )

    return results

# ===== 读取所有语料 =====
def load_corpus():
    all_items = []

    # txt
    for file in sorted(glob.glob("cam*.txt")):
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                all_items.extend(parse_text_with_labels(text, file))
        except Exception:
            pass

    # docx
    try:
        import docx
        for file in sorted(glob.glob("cam*.docx")):
            try:
                doc = docx.Document(file)
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                all_items.extend(parse_text_with_labels(text, file))
            except Exception:
                pass
    except Exception:
        pass

    return all_items

corpus_items = load_corpus()

# ===== 查句子 =====
def find_sentence(word):
    word = word.strip()
    if not word:
        return None

    # 短语：直接宽松匹配
    if " " in word or "-" in word:
        low_word = word.lower()
        for item in corpus_items:
            if low_word in item["sentence"].lower():
                return item
        return None

    # 单词：严格匹配
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for item in corpus_items:
        if pattern.search(item["sentence"]):
            return item

    # 常见词形变化
    variants = [
        word,
        word + "s",
        word + "ed",
        word + "ing",
        word[:-1] + "ing" if word.endswith("e") else word + "ing"
    ]

    for v in variants:
        pattern_v = re.compile(rf"\b{re.escape(v)}\b", re.IGNORECASE)
        for item in corpus_items:
            if pattern_v.search(item["sentence"]):
                return item

    return None

# ===== AI 补充：只负责 IPA / 中文解释 / 中文翻译 =====
def enrich(word, sentence):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "你是雅思词汇书编辑。只输出固定格式，不要解释，不要加废话。"
            },
            {
                "role": "user",
                "content": f"""
请为下面这个词补充信息，只输出以下三项：

IPA: ...
中文解释: ...
例句翻译: ...

词：{word}
例句：{sentence if sentence else "无"}
"""
            }
        ]
    )

    text = response.choices[0].message.content.strip()

    ipa = ""
    meaning_cn = ""
    example_cn = ""

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("IPA:"):
            ipa = line.replace("IPA:", "").strip()
        elif line.startswith("中文解释:"):
            meaning_cn = line.replace("中文解释:", "").strip()
        elif line.startswith("例句翻译:"):
            example_cn = line.replace("例句翻译:", "").strip()

    return ipa, meaning_cn, example_cn

# ===== UI =====
words = load_words()

st.write(f"当前词表数量: {len(words)}")
st.write(f"已加载语料句子数量: {len(corpus_items)}")

if st.button("Generate"):
    if not words:
        st.error("没有词表")
    elif not corpus_items:
        st.error("没有成功加载剑桥语料，请检查 cam 文件是否已上传到和 app.py 同一层")
    else:
        found = 0

        for i, word in enumerate(words[:50], 1):
            st.markdown(f"## {i}. {word}")

            item = find_sentence(word)

            if item:
                found += 1
                sentence = item["sentence"]
                source = item["source"]
            else:
                sentence = ""
                source = ""

            ipa, meaning_cn, example_cn = enrich(word, sentence)

            st.write(f"**IPA**: {ipa}")
            st.write(f"**中文解释**: {meaning_cn}")

            if source:
                st.write(f"**来源**: {source}")
            else:
                st.write("**来源**: 未找到")

            if sentence:
                st.write(f"**英文例句**: {sentence}")
            else:
                st.write("**英文例句**: 未找到")

            if example_cn:
                st.write(f"**中文翻译**: {example_cn}")
            else:
                st.write("**中文翻译**: 未找到")

            st.markdown("---")

        st.success(f"本次匹配成功: {found}/50")
