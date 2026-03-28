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
                messages=[
                    {
                        "role": "user",
                        "content": f"Write a detailed book outline about {topic}"
                    }
                ],
                model="llama-3.3-70b-versatile",
            )
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(str(e))
