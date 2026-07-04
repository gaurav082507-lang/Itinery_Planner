from dotenv import load_dotenv
load_dotenv()
import os,requests
from langchain.tools import tool
from rich import print
API_KEY=os.getenv("SEARCHAPI_API_KEY")
@tool
def get_flight(departure:str,arrival:str,date:str)->str:
    """This is a tool which helps to fetch live flight data for future and
     and input include the departure and arrival airport iata codes it must be in iata codes
     and date should be in the format of YYYY-MM-DD"""
    url=f"https://www.searchapi.io/api/v1/search?engine=google_flights&flight_type=one_way&departure_id={departure}&arrival_id={arrival}&outbound_date={date}&api_key={API_KEY}"
    response=requests.get(url=url)
    data=response.json()
    if "error" in data:
        return f"Error: {data['error']}"

    best_flights = data.get("best_flights", [])

    if not best_flights:
        return "No flights found for this route/date."

    flight_strings = []

    for option in best_flights:
        price = option.get("price")
        total_duration = option.get("total_duration")
        legs = option.get("flights", [])

        if not legs:
            continue

        leg_summaries = []
        for leg in legs:
            airline = leg.get("airline")
            flight_number = leg.get("flight_number")
            dep = leg.get("departure_airport", {})
            arr = leg.get("arrival_airport", {})
            airplane = leg.get("airplane")

            leg_summaries.append(
                f"{airline} {flight_number} ({airplane}): "
                f"{dep.get('id')} {dep.get('time')} -> "
                f"{arr.get('id')} {arr.get('time')}"
            )

        stops = len(legs) - 1
        stop_text = "Non-stop" if stops == 0 else f"{stops} stop(s)"

        summary = (
            f"${price} | {stop_text} | {total_duration} min total | "
            + " | ".join(leg_summaries)
        )

        flight_strings.append(summary)

    return "\n".join(flight_strings)

@tool
def get_hotel(city:str,check_in:str,check_out:str)->str:
    """This is a tool will return the options of hotels available to the 
    user for with the given input city in string format and also the check-in and check out dates 
    in the format of YYYY-MM-DD"""
    url=f"https://www.searchapi.io/api/v1/search?engine=google_hotels&q={city}&check_in_date={check_in}&check_out_date={check_out}&api_key={API_KEY}"
    reponse=requests.get(url)
    data=reponse.json()
    if "error" in data:
        return f"Error: {data['error']}"

    properties = data.get("properties", [])

    if not properties:
        return "No hotels found for this location/dates."

    hotel_strings = []

    for hotel in properties:
        name = hotel.get("name")
        hotel_type = hotel.get("type")
        rating = hotel.get("overall_rating")
        reviews = hotel.get("reviews")
        hotel_class = hotel.get("hotel_class")

        price_per_night = hotel.get("rate_per_night", {}).get("lowest")
        total_price = hotel.get("total_rate", {}).get("lowest")

        amenities = hotel.get("amenities", [])
        amenities_text = ", ".join(amenities[:5]) if amenities else "N/A"

        link = hotel.get("link")

        summary = (
            f"{name} ({hotel_type}) | {hotel_class or 'N/A'} star | "
            f"Rating: {rating} ({reviews} reviews)\n"
            f"  Price/night: {price_per_night} | Total: {total_price}\n"
            f"  Amenities: {amenities_text}\n"
            f"  Link: {link}"
        )

        hotel_strings.append(summary)

    return "\n\n".join(hotel_strings)
