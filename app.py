import streamlit as st
from groq import Groq
import os
import re
import glob
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

st.title("IELTS Vocabulary Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

# =========================
# 基础工具
# =========================
def normalize_text(text):
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\xa0": " ",
        "\t": " ",
        "\r": "\n",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()

def format_book_label(filename):
    m = re.search(r"cam(\d+)", filename.lower())
    if m:
        return f"IELTS {m.group(1)}"
    return filename

def extract_test_and_passage(line):
    line_u = line.upper()

    test_num = None
    passage_num = None

    m_test = re.search(r"TEST\s*(\d+)", line_u)
    if m_test:
        test_num = m_test.group(1)

    m_passage = re.search(r"READING\s*PASSAGE\s*(\d+)", line_u)
    if m_passage:
        passage_num = m_passage.group(1)

    return test_num, passage_num

def build_source(filename, current_test, current_passage):
    parts = [format_book_label(filename)]
    if current_test:
        parts.append(f"Test {current_test}")
    if current_passage:
        parts.append(f"Reading Passage {current_passage}")
    return "_".join(parts)

def build_variants(word):
    word = word.strip().lower()
    variants = {word}

    if " " in word or "-" in word:
        return list(variants)

    variants.add(word + "s")
    variants.add(word + "ed")
    variants.add(word + "ing")

    if word.endswith("e"):
        variants.add(word[:-1] + "ing")

    if word.endswith("y") and len(word) > 2:
        variants.add(word[:-1] + "ies")

    return list(variants)

def line_matches_word(line, word):
    if not line:
        return False

    variants = build_variants(word)
    for v in variants:
        pattern = re.compile(rf"\b{re.escape(v)}\b", re.IGNORECASE)
        if pattern.search(line):
            return True
    return False

# =========================
# 读取文件
# =========================
def read_txt_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return normalize_text(f.read())

def read_rtf_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # 极简 RTF 清洗，够当前用途
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return normalize_text(text)

def read_docx_file(path):
    texts = []
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    for para in root.findall(".//w:p", ns):
        runs = para.findall(".//w:t", ns)
        line = "".join([r.text for r in runs if r.text])
        line = line.strip()
        if line:
            texts.append(line)

    return normalize_text("\n".join(texts))

# =========================
# 读取词表
# =========================
def load_words():
    if not os.path.exists("ielts_words.txt"):
        return []

    with open("ielts_words.txt", "r", encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.readlines() if w.strip()]

    return words

# =========================
# 建立语料块
# 每个块都带 source
# =========================
def parse_corpus_text(text, filename):
    text = normalize_text(text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    chunks = []
    current_test = None
    current_passage = None

    for i, line in enumerate(lines):
        # 先更新标签
        t_num, p_num = extract_test_and_passage(line)
        if t_num:
            current_test = t_num
        if p_num:
            current_passage = p_num

        # 建立上下文块：当前行 + 后2行
        block_lines = [line]
        if i + 1 < len(lines):
            block_lines.append(lines[i + 1])
        if i + 2 < len(lines):
            block_lines.append(lines[i + 2])

        block_text = " ".join(block_lines)
        block_text = re.sub(r"\s+", " ", block_text).strip()

        # 过滤太短和纯标题
        if len(block_text) >= 30:
            chunks.append({
                "text": block_text,
                "source": build_source(filename, current_test, current_passage)
            })

    return chunks

def load_corpus_chunks():
    all_chunks = []
    loaded_files = []

    # txt
    for path in sorted(glob.glob("cam*.txt")):
        try:
            text = read_txt_file(path)
            chunks = parse_corpus_text(text, os.path.basename(path))
            if chunks:
                all_chunks.extend(chunks)
                loaded_files.append(os.path.basename(path))
        except Exception:
            pass

    # rtf
    for path in sorted(glob.glob("cam*.rtf")):
        try:
            text = read_rtf_file(path)
            chunks = parse_corpus_text(text, os.path.basename(path))
            if chunks:
                all_chunks.extend(chunks)
                loaded_files.append(os.path.basename(path))
        except Exception:
            pass

    # docx
    for path in sorted(glob.glob("cam*.docx")):
        try:
            text = read_docx_file(path)
            chunks = parse_corpus_text(text, os.path.basename(path))
            if chunks:
                all_chunks.extend(chunks)
                loaded_files.append(os.path.basename(path))
        except Exception:
            pass

    return all_chunks, loaded_files

corpus_chunks, loaded_files = load_corpus_chunks()

# =========================
# 查例句
# =========================
def find_example(word):
    # 先严格匹配
    for item in corpus_chunks:
        if line_matches_word(item["text"], word):
            return item

    # 再宽松匹配（针对词组）
    low_word = word.lower().strip()
    if " " in low_word or "-" in low_word:
        for item in corpus_chunks:
            if low_word in item["text"].lower():
                return item

    return None

# =========================
# AI 补充 IPA / 中文解释 / 翻译
# =========================
def enrich_word(word, example_text):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "你是雅思词汇书编辑。只按固定格式输出，不要解释，不要废话。"
            },
            {
                "role": "user",
                "content": f"""
请为下面这个词补充信息，只输出以下三项：

IPA: ...
中文解释: ...
中文翻译: ...

词：{word}
英文例句：{example_text if example_text else "无"}
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
        elif line.startswith("中文翻译:"):
            example_cn = line.replace("中文翻译:", "").strip()

    return ipa, meaning_cn, example_cn

# =========================
# UI
# =========================
words = load_words()

st.write(f"当前词表数量: {len(words)}")
st.write(f"已加载语料文件: {', '.join(loaded_files) if loaded_files else '无'}")
st.write(f"已加载语料块数量: {len(corpus_chunks)}")

if st.button("Generate"):
    if not words:
        st.error("没有词表")
    elif not corpus_chunks:
        st.error("没有成功加载剑桥语料，请检查 cam 文件是否已上传到和 app.py 同一层")
    else:
        found_count = 0

        for i, word in enumerate(words[:50], 1):
            st.markdown(f"## {i}. {word}")

            item = find_example(word)

            if item:
                example_en = item["text"]
                source = item["source"]
                found_count += 1
            else:
                example_en = ""
                source = "未找到"

            ipa, meaning_cn, example_cn = enrich_word(word, example_en)

            st.write(f"**IPA**: {ipa if ipa else '未生成'}")
            st.write(f"**中文解释**: {meaning_cn if meaning_cn else '未生成'}")
            st.write(f"**来源**: {source}")
            st.write(f"**英文例句**: {example_en if example_en else '未找到'}")
            st.write(f"**中文翻译**: {example_cn if example_cn else '未生成'}")

            st.markdown("---")

        st.success(f"本次 50 个词中，成功匹配到 {found_count} 个例句。")
