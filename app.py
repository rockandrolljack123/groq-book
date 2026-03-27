import streamlit as st
from groq import Groq
import os

st.title("AI Book Generator")

# 从 secrets 读取 API key
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in Secrets")
    st.stop()

client = Groq(api_key=api_key)

topic = st.text_input("Enter your book topic:")

if st.button("Generate Book"):
    if topic:
        with st.spinner("Generating..."):
            try:
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "user", "content": f"Write a detailed book outline about {topic}"}
                    ]
                )
                result = response.choices[0].message.content
                st.write(result)

            except Exception as e:
                st.error(str(e))
    else:
        st.warning("Please enter a topic")
