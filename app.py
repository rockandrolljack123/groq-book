import streamlit as st
from groq import Groq

st.title("AI Book Generator")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

topic = st.text_input("Enter your book topic:")

if st.button("Generate Book"):
    if not topic.strip():
        st.warning("Please enter a topic")
    else:
        try:
           response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    max_tokens=6000,
    messages=[
        {
            "role": "user",
            "content": f"""
你是一名出版级英语词汇书作者。

任务：围绕【{topic}】写一本完整的雅思核心词汇书的一章内容。

要求：
1. 至少生成50个词（必须达到50个）
2. 每个词必须包含：
   - 单词
   - 音标
   - 中文解释
   - 英文例句
   - 中文翻译
   - 2-3个同义替换
3. 内容必须是“成书级”，不能是简单示例
4. 输出要结构清晰，适合直接出版
5. 不允许中途停止，必须写完50个词

开始写：
"""
        }
    ]
)
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(str(e))
