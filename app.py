import io
import re
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from tools import get_flight, get_hotel, get_places
from langchain_mistralai import ChatMistralAI

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Voyagent · AI Travel Concierge",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* ---- Global ---- */
        .stApp {
            background: radial-gradient(circle at 20% 0%, #0f1729 0%, #0a0e1a 45%, #06080f 100%);
        }
        #MainMenu, footer {visibility: hidden;}

        /* ---- Hero banner ---- */
        .voyagent-hero {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 45%, #d946ef 100%);
            border-radius: 20px;
            padding: 2.4rem 2.6rem;
            margin-bottom: 1.6rem;
            box-shadow: 0 20px 45px -20px rgba(139, 92, 246, 0.55);
        }
        .voyagent-hero h1 {
            color: white;
            font-size: 2.3rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .voyagent-hero p {
            color: rgba(255,255,255,0.9);
            font-size: 1.02rem;
            margin-top: 0.5rem;
            margin-bottom: 0;
        }
        .voyagent-badge {
            display: inline-block;
            background: rgba(255,255,255,0.18);
            color: white;
            padding: 0.28rem 0.85rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 0.5rem;
            margin-top: 0.9rem;
            backdrop-filter: blur(6px);
        }

        /* ---- Example prompt card ---- */
        .example-card {
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.35);
            border-radius: 14px;
            padding: 1rem 1.3rem;
            color: #d8dcff;
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }
        .example-card b { color: #a5b4fc; }

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10152b 0%, #0a0e1a 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        .sidebar-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #f1f2ff;
            margin-bottom: 0.1rem;
        }
        .sidebar-sub {
            color: #9ca3d4;
            font-size: 0.88rem;
            line-height: 1.5;
            margin-bottom: 1rem;
        }
        .sidebar-section-title {
            color: #a5b4fc;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 1.3rem;
            margin-bottom: 0.5rem;
        }
        .feature-pill {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 10px;
            padding: 0.55rem 0.75rem;
            margin-bottom: 0.5rem;
            color: #d1d5f5;
            font-size: 0.85rem;
        }
        .credit-box {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin-top: 1.2rem;
            text-align: center;
        }
        .credit-box a {
            color: #a5b4fc;
            text-decoration: none;
            font-weight: 600;
        }
        .credit-box a:hover { text-decoration: underline; }

        /* ---- Chat bubbles ---- */
        div[data-testid="stChatMessage"] {
            border-radius: 16px;
            padding: 0.3rem 0.4rem;
        }

        /* ---- Footer ---- */
        .voyagent-footer {
            text-align: center;
            color: #6b7280;
            font-size: 0.85rem;
            padding: 1.5rem 0 0.5rem 0;
        }
        .voyagent-footer a {
            color: #a5b4fc;
            text-decoration: none;
            font-weight: 600;
        }
        .voyagent-footer a:hover { text-decoration: underline; }
    </style>
    """,
    unsafe_allow_html=True,
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


def _clean_for_pdf(text: str) -> str:
    """Reportlab's default fonts don't include the ₹ glyph (renders as a
    black box), so swap it for 'Rs.' before rendering."""
    return text.replace("₹", "Rs. ")


def _markdown_line_to_html(line: str) -> str:
    """Very small markdown -> reportlab-inline-html converter, just enough
    for headers, bold, and bullets that the agent tends to produce."""
    line = line.strip()
    # bold **text**
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    return line


def build_itinerary_pdf(itinerary_text: str, trip_query: str = "") -> bytes:
    """Builds a nicely formatted PDF from the agent's itinerary text and
    returns the raw PDF bytes, ready for st.download_button."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VoyagentTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#4c1d95"),
        fontSize=22,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "VoyagentSubtitle",
        parent=styles["Normal"],
        textColor=colors.HexColor("#6b7280"),
        fontSize=10,
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "VoyagentH2",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#6d28d9"),
        fontSize=14,
        spaceBefore=14,
        spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        "VoyagentH3",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#7c3aed"),
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "VoyagentBody",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=15,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "VoyagentBullet",
        parent=body_style,
        leftIndent=14,
        bulletIndent=4,
    )

    story = []
    story.append(Paragraph("🧭 Voyagent — Trip Itinerary", title_style))
    generated_on = datetime.now().strftime("%d %b %Y, %I:%M %p")
    if trip_query:
        story.append(Paragraph(_clean_for_pdf(trip_query), subtitle_style))
    story.append(Paragraph(f"Generated on {generated_on}", subtitle_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#c4b5fd"), thickness=1))
    story.append(Spacer(1, 10))

    text = _clean_for_pdf(itinerary_text)

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            story.append(Spacer(1, 6))
            continue

        stripped = line.strip()

        if stripped.startswith("### "):
            story.append(Paragraph(_markdown_line_to_html(stripped[4:]), h3_style))
        elif stripped.startswith("## "):
            story.append(Paragraph(_markdown_line_to_html(stripped[3:]), h2_style))
        elif stripped.startswith("# "):
            story.append(Paragraph(_markdown_line_to_html(stripped[2:]), h2_style))
        elif stripped.startswith(("- ", "* ")):
            story.append(
                Paragraph(f"&bull;&nbsp; {_markdown_line_to_html(stripped[2:])}", bullet_style)
            )
        else:
            story.append(Paragraph(_markdown_line_to_html(stripped), body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


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
    st.markdown('<div class="sidebar-title">🧭 Voyagent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-sub">Your AI travel concierge — flights, stays, '
        "and sightseeing, planned into one itinerary.</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">What it does</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="feature-pill">✈️ &nbsp; Live flight search &amp; pricing</div>
        <div class="feature-pill">🏨 &nbsp; Hotel comparison by price &amp; rating</div>
        <div class="feature-pill">📍 &nbsp; Real tourist attractions per city</div>
        <div class="feature-pill">🗓️ &nbsp; Day-by-day itinerary builder</div>
        <div class="feature-pill">💰 &nbsp; Transparent cost breakdown</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">How to use</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="feature-pill">1️⃣ &nbsp; Share your departure &amp; destination</div>
        <div class="feature-pill">2️⃣ &nbsp; Give your travel dates</div>
        <div class="feature-pill">3️⃣ &nbsp; Mention travelers &amp; budget</div>
        <div class="feature-pill">4️⃣ &nbsp; Get your full trip plan</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">Powered by</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="feature-pill">🧠 &nbsp; Mistral (mistral-small-2603)</div>
        <div class="feature-pill">🔗 &nbsp; LangChain Agent</div>
        <div class="feature-pill">🌐 &nbsp; Live travel data via SearchAPI</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️  Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        """
        <div class="credit-box">
            Built by <b>Gaurav Gupta</b><br>
            <a href="https://www.linkedin.com/in/gaurav-gupta-79754a377" target="_blank">🔗 View LinkedIn Profile</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="voyagent-hero">
        <h1>🧭 Voyagent — Your AI Travel Concierge</h1>
        <p>Tell me where you want to go — I'll find flights, hotels, and things to do,
        then build you a complete, budget-aware itinerary.</p>
        <span class="voyagent-badge">⚡ Live pricing</span>
        <span class="voyagent-badge">🤖 Agentic AI</span>
        <span class="voyagent-badge">🗺️ Real destinations</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chat history / example prompt
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    st.markdown(
        """
        <div class="example-card">
        👋 &nbsp;Try something like: <b>"Plan a 4-day trip from Delhi to Jaipur
        from 15th to 19th August for 2 people, budget around ₹40,000."</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

for i, msg in enumerate(st.session_state.messages):
    avatar = "🧑‍💼" if msg["role"] == "user" else "🧭"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            pdf_bytes = build_itinerary_pdf(msg["content"])
            st.download_button(
                label="📄 Download this itinerary as PDF",
                data=pdf_bytes,
                file_name=f"voyagent_itinerary_{i+1}.pdf",
                mime="application/pdf",
                key=f"pdf_download_{i}",
                use_container_width=False,
            )

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Tell me about your trip...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🧭"):
        with st.spinner("Searching flights, hotels, and places..."):
            try:
                response = agent.invoke({"messages": [("user", user_input)]})
                reply = response["messages"][-1].content
            except Exception as e:
                reply = f"⚠️ Something went wrong while planning your trip: {e}"
        st.markdown(reply)

        pdf_bytes = build_itinerary_pdf(reply)
        st.download_button(
            label="📄 Download this itinerary as PDF",
            data=pdf_bytes,
            file_name=f"voyagent_itinerary_{len(st.session_state.messages)+1}.pdf",
            mime="application/pdf",
            key=f"pdf_download_new_{len(st.session_state.messages)}",
            use_container_width=False,
        )

    st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="voyagent-footer">
        Voyagent · AI Travel Concierge &nbsp;|&nbsp; Built by <b>Gaurav Gupta</b> &nbsp;|&nbsp;
        <a href="https://www.linkedin.com/in/gaurav-gupta-79754a377" target="_blank">LinkedIn</a>
    </div>
    """,
    unsafe_allow_html=True,
)
