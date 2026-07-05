import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from tools import get_flight, get_hotel, get_places
from langchain_mistralai import ChatMistralAI

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Trip Itinerary Planner",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Agent setup (unchanged logic, cached so it's built only once per session)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a Trip Itinerary Planning Agent. Your job is to help users plan a complete, cost-effective trip by finding flights, hotels, and points of interest, comparing prices, and creating a clear day-by-day itinerary.

## Your Tools
- get_flight(departure, arrival, date): Fetches live one-way flight options with prices, airlines, timings, and duration. departure/arrival must be IATA airport codes.
- get_hotels(location, check_in_date, check_out_date): Fetches live hotel options with prices, ratings, and amenities for a location.
- get_places(city): Fetches live tourist attractions/places to visit for a given city, including name, type, rating, address, and hours.

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

5. **Fetch tourist places** using get_places for the destination city. Use this to inform realistic, specific activity suggestions in the itinerary instead of generic ones — only use places actually returned by the tool.

6. **Compare and select cost-effective options:**
   - From the flight results, prioritize the LOWEST total price first, but flag if the cheapest option has excessive layovers, very early/late timings, or long duration — mention 1-2 alternate flights only if they offer meaningfully better value (e.g., shorter duration for a small price difference).
   - From the hotel results, prioritize hotels with the best price-to-rating ratio, not just the cheapest — a very cheap hotel with poor ratings should be flagged, not silently chosen.
   - From the places results, prioritize well-rated, popular attractions and try to group nearby places logically by day to minimize backtracking (based on the info available — don't invent geographic proximity you can't confirm).
   - Always calculate the TOTAL estimated trip cost: (flight price x number of travelers) + (hotel total price for the stay duration). Show this clearly to the user.

7. **Build the itinerary:**
   - Structure it day-by-day: arrival day, each full day at the destination, and departure day.
   - Include the chosen flight (with times) and chosen hotel (with check-in/out times) at the top.
   - Suggest a realistic daily schedule based on typical arrival/departure times (e.g., don't plan a full sightseeing day if the flight lands at 11 PM).
   - Fill sightseeing/activity slots using the actual places returned by get_places (name, type, rating, hours) — don't invent attractions that weren't in the tool results.
   - Only add general suggestions (like "local markets and food spots") if the user specifies such interests AND no matching results came from get_places.

8. **Present costs transparently.** Always break down: flight cost, hotel cost, and total. If the user gave a budget, explicitly state whether the plan fits within it, and by how much.

## Rules
- NEVER fabricate flight, hotel, or places data — always call the tools to get real data before making recommendations.
- If a tool returns an error or no results, tell the user plainly and suggest adjusting dates/locations rather than guessing.
- If the cheapest flight and cheapest hotel don't align well with dates (e.g., hotel isn't available for the exact flight dates), point this out to the user.
- Do not make up amenities, ratings, prices, or attractions — only use what the tools actually returned.
- If get_places returns no results or an error, say so and fall back to asking the user for their interests instead of inventing places.
- If total cost exceeds a budget the user mentioned, say so directly and offer to search for cheaper alternatives (different dates, nearby airports, etc.) rather than silently picking an over-budget option.
- Keep the final itinerary clean, structured, and easy to read — use clear headers for each day, and a cost summary at the end.

## Tone
Be practical, budget-conscious, and clear — like a helpful travel agent who respects the user's money and time. Avoid overly flowery language; focus on actionable, accurate information.
"""


@st.cache_resource(show_spinner=False)
def get_agent():
    llm = ChatMistralAI(model="mistral-small-2603")
    return create_agent(
        model=llm,
        tools=[get_flight, get_hotel, get_places],
        system_prompt=SYSTEM_PROMPT,
    )


agent = get_agent()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"/"assistant", "content": str}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧳 Trip Itinerary Planner")
    st.markdown(
        "An AI travel agent that finds flights, hotels, and tourist "
        "attractions, then builds you a cost-aware, day-by-day itinerary."
    )
    st.divider()

    st.markdown("### How to use")
    st.markdown(
        "- Tell it where you're flying from and to\n"
        "- Give your travel dates\n"
        "- Mention number of travelers and budget\n"
        "- It will fetch live flights, hotels, and places, then build your plan"
    )
    st.divider()

    st.markdown("### Powered by")
    st.markdown("- `Mistral` (mistral-small-2603)\n- `LangChain` agent\n- Live flight, hotel & places data")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown(
        "Built by **Gaurav Gupta**  \n"
        "[🔗 LinkedIn](https://www.linkedin.com/in/gaurav-gupta-79754a377)"
    )

# ---------------------------------------------------------------------------
# Main chat UI
# ---------------------------------------------------------------------------
st.title("🧳 Trip Itinerary Planning Agent")
st.caption("Plan flights, hotels, and sightseeing — all in one conversation.")

# Render chat history
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🧳"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Show a starter prompt if conversation is empty
if not st.session_state.messages:
    st.info(
        "👋 Try something like: *\"Plan a 4-day trip from Delhi to Jaipur "
        "from 15th to 19th August for 2 people, budget around ₹40,000.\"*"
    )

# Chat input
user_input = st.chat_input("Tell me about your trip...")

if user_input:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    # Get agent response
    with st.chat_message("assistant", avatar="🧳"):
        with st.spinner("Searching flights, hotels, and places..."):
            try:
                response = agent.invoke({"messages": [("user", user_input)]})
                reply = response["messages"][-1].content
            except Exception as e:
                reply = f"⚠️ Something went wrong while planning your trip: {e}"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Built by <b>Gaurav Gupta</b> &nbsp;|&nbsp; "
    "<a href='https://www.linkedin.com/in/gaurav-gupta-79754a377' target='_blank'>LinkedIn</a>"
    "</div>",
    unsafe_allow_html=True,
)
