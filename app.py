from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from langchain.agents import create_agent
from tools import get_flight, get_hotel
from langchain_mistralai import ChatMistralAI


# ─────────────────────────────────────────────────────────────
# Agent setup — identical logic to the original script
# ─────────────────────────────────────────────────────────────
LLM = ChatMistralAI(model="mistral-small-2603")

SYSTEM_PROMPT = """You are a Trip Itinerary Planning Agent. Your job is to help users plan a complete, cost-effective trip by finding flights and hotels, comparing prices, and creating a clear day-by-day itinerary.

## Your Tools
- get_flight(departure, arrival, date): Fetches live one-way flight options with prices, airlines, timings, and duration. departure/arrival must be IATA airport codes.
- get_hotels(location, check_in_date, check_out_date): Fetches live hotel options with prices, ratings, and amenities for a location.

## Your Process
1. **Gather requirements first.** If the user hasn't provided the following, ask for them before calling any tool:
   - Departure city/airport
   - Destination city/airport
   - Travel dates (departure and return, or just departure if one-way)
   - Number of travelers
   - Approximate budget (if not given, assume a moderate/budget-conscious traveler)

2. **Convert city names to IATA codes** if the user gives city names instead of airport codes. Use well-known codes (e.g., Jaipur = JAI, Delhi = DEL, Mumbai = BOM). If unsure, ask the user to confirm the airport.

3. **Fetch flights** using get_flight for the outbound date (and return date if round-trip, calling it twice — once for each direction).

4. **Fetch hotels** using get_hotels for the destination city and the given check-in/check-out dates.

5. **Compare and select cost-effective options:**
   - From the flight results, prioritize the LOWEST total price first, but flag if the cheapest option has excessive layovers, very early/late timings, or long duration — mention 1-2 alternate flights only if they offer meaningfully better value (e.g., shorter duration for a small price difference).
   - From the hotel results, prioritize hotels with the best price-to-rating ratio, not just the cheapest — a very cheap hotel with poor ratings should be flagged, not silently chosen.
   - Always calculate the TOTAL estimated trip cost: (flight price x number of travelers) + (hotel total price for the stay duration). Show this clearly to the user.

6. **Build the itinerary:**
   - Structure it day-by-day: arrival day, each full day at the destination, and departure day.
   - Include the chosen flight (with times) and chosen hotel (with check-in/out times) at the top.
   - Suggest a realistic daily schedule based on typical arrival/departure times (e.g., don't plan a full sightseeing day if the flight lands at 11 PM).
   - Keep activity suggestions general and reasonable unless the user specifies interests (e.g., "add local markets and food spots" only if relevant to the destination).

7. **Present costs transparently.** Always break down: flight cost, hotel cost, and total. If the user gave a budget, explicitly state whether the plan fits within it, and by how much.

## Rules
- NEVER fabricate flight or hotel data — always call the tools to get real data before making recommendations.
- If a tool returns an error or no results, tell the user plainly and suggest adjusting dates/locations rather than guessing.
- If the cheapest flight and cheapest hotel don't align well with dates (e.g., hotel isn't available for the exact flight dates), point this out to the user.
- Do not make up amenities, ratings, or prices — only use what the tool actually returned.
- If total cost exceeds a budget the user mentioned, say so directly and offer to search for cheaper alternatives (different dates, nearby airports, etc.) rather than silently picking an over-budget option.
- Keep the final itinerary clean, structured, and easy to read — use clear headers for each day, and a cost summary at the end.

## Tone
Be practical, budget-conscious, and clear — like a helpful travel agent who respects the user's money and time. Avoid overly flowery language; focus on actionable, accurate information.
"""

agent = create_agent(
    model=LLM,
    tools=[get_flight, get_hotel],
    system_prompt=SYSTEM_PROMPT,
)


# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Waypoint — Trip Itinerary Planner",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────
# Styling — boarding-pass / flight-path inspired system
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg:        #10171A;
        --bg-panel:  #161F23;
        --ink:       #ECEAE3;
        --ink-dim:   #8FA0A3;
        --amber:     #D9A441;
        --teal:      #4FA69C;
        --line:      #223034;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: var(--bg);
    }

    /* ---- Header ---- */
    .wp-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        padding-bottom: 0.6rem;
        margin-bottom: 0.4rem;
        border-bottom: 1px dashed var(--line);
    }
    .wp-brand {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.9rem;
        letter-spacing: -0.02em;
        color: var(--ink);
    }
    .wp-brand span { color: var(--amber); }
    .wp-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: var(--ink-dim);
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    /* ---- Route strip (signature element) ---- */
    .wp-route {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: var(--teal);
        margin: 0.9rem 0 1.4rem 0;
        padding: 0.55rem 0.9rem;
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: 6px;
    }
    .wp-route .dot { color: var(--amber); }
    .wp-route .dashline {
        flex: 1;
        border-top: 1px dashed var(--line);
        height: 0;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: var(--bg-panel);
        border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--amber);
        font-size: 1rem;
        letter-spacing: 0.01em;
    }
    .wp-step {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--ink-dim);
        border-left: 2px solid var(--teal);
        padding: 0.15rem 0 0.15rem 0.6rem;
        margin-bottom: 0.55rem;
    }
    .wp-step b { color: var(--ink); }

    /* ---- Chat bubbles ---- */
    div[data-testid="stChatMessage"] {
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 0.3rem 0.4rem;
    }

    /* ---- Chat input ---- */
    div[data-testid="stChatInput"] textarea {
        font-family: 'Inter', sans-serif;
    }

    /* ---- Buttons ---- */
    .stButton button {
        background: transparent;
        border: 1px solid var(--teal);
        color: var(--teal);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        border-radius: 6px;
    }
    .stButton button:hover {
        background: var(--teal);
        color: var(--bg);
        border-color: var(--teal);
    }

    /* ---- Sidebar credit ---- */
    .wp-credit {
        margin-top: 1rem;
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: var(--ink-dim);
        line-height: 1.6;
    }
    .wp-credit b { color: var(--ink); }
    .wp-credit a {
        color: var(--teal);
        text-decoration: none;
        border-bottom: 1px dashed var(--teal);
    }
    .wp-credit a:hover { color: var(--amber); border-color: var(--amber); }

    /* ---- Perforated footer divider ---- */
    .wp-foot-divider {
        margin-top: 2rem;
        border-top: 1px dashed var(--line);
        text-align: center;
        padding-top: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: var(--ink-dim);
        letter-spacing: 0.08em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="wp-header">
        <div class="wp-brand">WAY<span>POINT</span></div>
        <div class="wp-tag">Cost-aware itinerary planning</div>
    </div>
    <div class="wp-route">
        <span class="dot">●</span> DEPARTURE
        <span class="dashline"></span>
        ✈
        <span class="dashline"></span>
        DESTINATION <span class="dot">●</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### How it works")
    st.markdown(
        """
        <div class="wp-step">01 — <b>Tell me your trip</b><br>departure, destination, dates, travelers, budget</div>
        <div class="wp-step">02 — <b>Live search</b><br>real flight & hotel prices are pulled in</div>
        <div class="wp-step">03 — <b>Cost check</b><br>options are compared for best value</div>
        <div class="wp-step">04 — <b>Itinerary</b><br>day-by-day plan with full cost breakdown</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    if st.button("↺ Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.markdown(
        '<div class="wp-foot-divider">✂ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ✂<br>POWERED BY LIVE FLIGHT &amp; HOTEL DATA</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="wp-credit">
            Made by <b>Gaurav</b><br>
            <a href="https://www.linkedin.com/in/gaurav-gupta-79754a377" target="_blank">LinkedIn ↗</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# Chat state
# ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render prior turns
for msg in st.session_state.messages:
    avatar = "🧭" if msg["role"] == "assistant" else "🧳"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Empty state
if not st.session_state.messages:
    st.info(
        "Tell me where you're headed — e.g. *\"Plan a trip from Jaipur to Goa, "
        "10th to 15th July, budget around ₹15000 for 2 people\"*",
        icon="🧭",
    )

# ─────────────────────────────────────────────────────────────
# Chat input — same single-turn agent.invoke logic as original
# ─────────────────────────────────────────────────────────────
plan = st.chat_input("Where are you headed?")

if plan:
    st.session_state.messages.append({"role": "user", "content": plan})
    with st.chat_message("user", avatar="🧳"):
        st.markdown(plan)

    with st.chat_message("assistant", avatar="🧭"):
        with st.spinner("Checking live flights & hotels…"):
            response = agent.invoke({"messages": [("user", plan)]})
            answer = response["messages"][-1].content
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
