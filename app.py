import streamlit as st
import re
import os

st.title("IELTS Vocabulary Book Generator")

# ===== 读取语料 =====
def load_corpus():
    sentences = []
    sources = []

    folder = "."

    for file in os.listdir(folder):
        if file.endswith(".txt"):
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()

                current_test = None
                current_passage = None

                lines = text.split("\n")

                for line in lines:
                    line_clean = line.strip()

                    # ===== 提取 Test =====
                    test_match = re.search(r"Test\s*(\d+)", line_clean, re.IGNORECASE)
                    if test_match:
                        current_test = test_match.group(1)

                    # ===== 提取 Passage（核心修复）=====
                    passage_match = re.search(r"Reading\s*Passage\s*(\d+)", line_clean, re.IGNORECASE)
                    if passage_match:
                        current_passage = passage_match.group(1)

                    # ===== 收集句子 =====
                    if len(line_clean) > 40 and "." in line_clean:
                        sentences.append(line_clean)
                        sources.append((current_test, current_passage, file))

    return sentences, sources


sentences, sources = load_corpus()

st.write(f"已加载语料句子数量: {len(sentences)}")

# ===== 示例词表 =====
word_list = ["ability", "abundant", "access", "accurate", "adapt"]

if st.button("Generate"):
    for i, word in enumerate(word_list, 1):
        found = False

        for idx, sent in enumerate(sentences):
            if word.lower() in sent.lower():
                test, passage, file = sources[idx]

                st.markdown(f"### {i}. {word}")
                st.write(f"来源：IELTS {file.replace('.txt','')} Test {test} Reading Passage {passage}")
                st.write(f"英文例句：{sent}")
                found = True
                break

        if not found:
            st.markdown(f"### {i}. {word}")
            st.write("⚠️ 未找到例句")
