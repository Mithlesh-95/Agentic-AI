import streamlit as st
import json
import requests
import os
import wikipediaapi
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()
# --------------------------------------------------
# OpenRouter Client
# --------------------------------------------------

client = OpenAI(
    api_key="sk-or-v1-5a7fc7b27c14430b50fe23853a0e07efb6a964dbfc6d61f93392a955fd7a7c7",
    base_url="https://openrouter.ai/api/v1"
)

# --------------------------------------------------
# Tools
# --------------------------------------------------

def get_weather(city: str):
    try:
        url = f"https://wttr.in/{city}?format=%C+%t"
        response = requests.get(url)

        if response.status_code == 200:
            return f"The weather in {city} is {response.text}"

        return "Weather service unavailable"

    except Exception as e:
        return str(e)


def run_command(cmd: str):
    try:
        return str(os.system(cmd))
    except Exception as e:
        return str(e)


def calculator(expression: str):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Calculation Error: {e}"


def search_wikipedia(query: str):
    try:
        wiki = wikipediaapi.Wikipedia(
            user_agent="WikiAssistant",
            language="en"
        )

        page = wiki.page(query)

        if page.exists():
            return page.summary[:1000]

        return f"No article found for {query}"

    except Exception as e:
        return str(e)


available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
    "calculator": calculator,
    "search_wikipedia": search_wikipedia
}

# --------------------------------------------------
# Prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are an AI Assistant.

Return JSON only.

Format:
{
    "step":"plan/action/output",
    "content":"text",
    "function":"tool_name",
    "input":"tool_input"
}

Available Tools:
- get_weather
- calculator
- search_wikipedia
- run_command

Always think step by step.
Use one step at a time.
"""

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(
    page_title="AI Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Agent")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Show old messages
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --------------------------------------------------
# User Input
# --------------------------------------------------

query = st.chat_input("Ask anything...")

if query:

    st.session_state.chat_history.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("user"):
        st.markdown(query)

    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("assistant"):

        status = st.status(
            "🧠 Thinking...",
            expanded=True
        )

        final_answer = ""

        
    while True:

        response = client.chat.completions.create(
            model="nex-agi/nex-n2-pro",
            messages=st.session_state.messages,
            response_format={"type": "json_object"},
            max_tokens=500
        )

        llm_response = response.choices[0].message.content

        status.write(f"🤖 Raw Response: {llm_response}")

        try:
            parsed = json.loads(llm_response)
        except Exception as e:
            status.error(f"JSON Error: {e}")
            break

        step = parsed.get("step")

        # ---------------- PLAN ----------------

        if step == "plan":

            plan_text = parsed.get("content", "")

            status.write(f"🧠 {plan_text}")

            st.session_state.messages.append({
                "role": "user",
                "content": "Continue to the next step."
            })

            continue

        # ---------------- ACTION ----------------

        elif step == "action":

            tool_name = parsed.get("function")
            tool_input = parsed.get("input")

            status.write(f"🛠️ Tool: {tool_name}")
            status.write(f"📥 Input: {tool_input}")

            if tool_name in available_tools:

                output = available_tools[tool_name](tool_input)

                status.write(f"✅ Output: {output}")

                st.session_state.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "step": "observe",
                        "output": output
                    })
                })

                continue

            else:

                status.error(f"Unknown Tool: {tool_name}")
                break

        # ---------------- OUTPUT ----------------

        elif step == "output":

            final_answer = parsed.get("content", "")

            status.update(
                label="✅ Completed",
                state="complete"
            )

            st.markdown(final_answer)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": final_answer
            })

            break

        else:

            status.error(f"Unknown Step: {step}")
            break

