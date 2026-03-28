import streamlit as st
from groq import Groq
import os
import re
import glob
import random

st.title("IELTS Vocabulary Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

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
# 句子词数统计
# =========================
def count_words(sentence):
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence))


# =========================
# 常见词形变化
# =========================
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


# =========================
# 判断句子是否命中词
# =========================
def sentence_matches_word(sentence, word):
    sentence_lower = sentence.lower()
    variants = build_variants(word)

    if " " in word or "-" in word:
        return word.lower() in sentence_lower

    for v in variants:
        pattern = re.compile(rf"\b{re.escape(v)}\b", re.IGNORECASE)
        if pattern.search(sentence):
            return True

    return False


# =========================
# 解析 clean txt
# 只读取 cam*.txt 和 clean*.txt
# 明确排除 ielts_words.txt
# =========================
def parse_clean_corpus():
    items = []

    txt_files = sorted(glob.glob("cam*.txt")) + sorted(glob.glob("clean*.txt"))

    seen_files = set()
    final_files = []
    for f in txt_files:
        base = os.path.basename(f)
        if base.lower() == "ielts_words.txt":
            continue
        if base not in seen_files:
            seen_files.add(base)
            final_files.append(f)

    title_pattern = re.compile(
        r"^###\s+(IELTS\d+)\s+(Test\d+)\s+(Reading\s+Passage\d+|Listening\s+Section\d+)\s*$",
        re.IGNORECASE
    )

    current_source = None

    for path in final_files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            m = title_pattern.match(line)
            if m:
                book = m.group(1)
                test = m.group(2)
                section = m.group(3)

                book = book.replace(" ", "")
                test = test.replace(" ", "")
                section = re.sub(r"\s+", " ", section).strip()
                section = section.replace("Passage ", "Passage")
                section = section.replace("Section ", "Section")

                current_source = f"{book} {test} {section}"
                continue

            # 只收“真正像句子”的正文
            if current_source:
                # 至少3个单词，避免把 ability 这种单独单词当句子
                if count_words(line) < 3:
                    continue

                # 必须包含空格，避免单个词
                if " " not in line:
                    continue

                items.append({
                    "sentence": line,
                    "source": current_source
                })

    return items


# =========================
# 选例句
# 规则：
# 1. 先找全部命中句
# 2. 优先 <= 20 词
# 3. 没有的话退到 <= 25 词
# 4. 同时尽量平衡不同 IELTS 册数
# 5. 最后固定随机，保证可复现
# =========================
def choose_example(word, corpus_items, usage_counter):
    matches = []

    for item in corpus_items:
        sentence = item["sentence"]
        source = item["source"]

        if sentence_matches_word(sentence, word):
            matches.append(item)

    if not matches:
        return None

    short_20 = [m for m in matches if count_words(m["sentence"]) <= 20]
    short_25 = [m for m in matches if count_words(m["sentence"]) <= 25]

    candidates = short_20 if short_20 else short_25 if short_25 else matches

    def book_key(source):
        m = re.search(r"(IELTS\d+)", source, re.IGNORECASE)
        return m.group(1).upper() if m else "UNKNOWN"

    min_used = None
    filtered = []

    for c in candidates:
        bk = book_key(c["source"])
        used = usage_counter.get(bk, 0)
        if min_used is None or used < min_used:
            min_used = used

    for c in candidates:
        bk = book_key(c["source"])
        if usage_counter.get(bk, 0) == min_used:
            filtered.append(c)

    rng = random.Random(word.lower())
    chosen = rng.choice(filtered)

    chosen_book = book_key(chosen["source"])
    usage_counter[chosen_book] = usage_counter.get(chosen_book, 0) + 1

    return chosen


# =========================
# AI 补 IPA / 中文解释 / 翻译
# =========================
def enrich_word(word, example_text):
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
# 主程序
# =========================
words = load_words()
corpus_items = parse_clean_corpus()

st.write(f"当前词表数量: {len(words)}")
st.write(f"已加载语料句子数量: {len(corpus_items)}")

if st.button("Generate"):
    if not words:
        st.error("没有词表")
        st.stop()

    if not corpus_items:
        st.error("没有成功加载 clean txt 语料")
        st.stop()

    usage_counter = {}
    found_count = 0

    for i, word in enumerate(words[:50], 1):
        st.markdown(f"## {i}. {word}")

        chosen = choose_example(word, corpus_items, usage_counter)

        if chosen:
            example_en = chosen["sentence"]
            source = chosen["source"]
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
