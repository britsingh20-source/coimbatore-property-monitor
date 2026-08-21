from __future__ import annotations

from typing import Any


CONTACT_NUMBER = "9003787621"
MISSING = {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def _value(value: Any, fallback: str = "Not specified — omit from video") -> str:
    text = str(value or "").strip()
    return fallback if text.upper() in MISSING else text


def build_veo_prompt(job: dict) -> str:
    prop = job.get("property") or {}
    location = _value(job.get("property_location"), "Coimbatore")
    property_type = _value(prop.get("property_type"), "Property")
    bhk = _value(prop.get("bhk"), "")
    land = _value(prop.get("land_area"))
    built_up = _value(prop.get("built_up_area"))
    facing = _value(prop.get("facing"))
    parking = _value(prop.get("parking"))
    approval = _value(prop.get("approval"))
    price = _value(prop.get("price"))
    source_url = _value(job.get("source_url"), "Source video supplied separately")
    facts = _value(job.get("verified_facts"), "Use only facts confirmed in the source video")

    return f"""First analyse the uploaded original property video frame-by-frame.

Identify only visually confirmed details: the exact exterior elevation, floor count, building colours and materials, gate, parking, entrance, hall, false ceiling, kitchen, bedrooms, bathrooms, staircase, terrace, doors, windows, flooring, neighbourhood and visible connections between areas. Never infer a feature or room connection that is not clearly visible.

VERIFIED PROPERTY INFORMATION
Source: {source_url}
Location: {location}
Property type: {property_type}
Bedrooms: {bhk}
Land area: {land}
Built-up area: {built_up}
Facing: {facing}
Parking: {parking}
Approval: {approval}
Price: {price}
Verified facts: {facts}

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 property advertisement based on the uploaded source video. Do not reuse source frames directly. Reconstruct the property using only its visually confirmed architectural identity. It must resemble genuine smartphone footage recorded by a local Coimbatore property broker, not an architectural render, slideshow or AI-image animation.

SHOT 1 — 0 TO 3 SECONDS
Create a realistic handheld smartphone approach from the verified local residential road toward the reconstructed property. Preserve the exact elevation, number of floors, colours, gate, windows, parking and surrounding environment visible in the source. Include only appropriate local details visible in the source, such as neighbouring houses, EB poles, road edges, drainage and parked two-wheelers. Do not redesign, beautify or enlarge the property.

SHOT 2 — 3 TO 5 SECONDS
Use a clean hard cut to the reconstructed gate, parking or portico. Create a natural short movement toward the main entrance. Preserve the actual tiles, pillars, gate design, parking dimensions, door and exterior materials. Do not open the door or create an exterior-to-interior morphing transition.

SHOT 3 — 5 TO 7.5 SECONDS
Use a clean hard cut to the strongest clearly verified interior area in the source. Reconstruct only that area with its confirmed proportions, ceiling, doors, windows, flooring, wall treatment, furniture and fixtures. Use a subtle handheld pan. Do not reveal another room unless the source clearly proves the physical connection.

SHOT 4 — 7.5 TO 9 SECONDS
Use a clean hard cut to the second-strongest clearly verified property feature. Preserve its exact visible layout, colours, materials and dimensions. If no second interior is clear, use another verified exterior, parking, staircase or terrace angle. Never invent a kitchen, bedroom, bathroom or amenity.

ENDING — 9 TO 10 SECONDS
Hard cut back to the reconstructed exterior. Display a clean, stable footer:
“{location} • {bhk} BHK {property_type}”
“{land} • {built_up}”
“{price}”
“SITE VISIT: {CONTACT_NUMBER}”

Keep the footer upright, sharp and stationary. Use a solid white or brand-coloured footer covering the bottom area.

VOICEOVER
Generate a natural, conversational Coimbatore Tamil male voice that mentions only the strongest verified property facts and ends exactly with:
“மேலும் details மற்றும் site visitக்கு {CONTACT_NUMBER} நம்பருக்கு call பண்ணுங்க!”

Use subtle neighbourhood ambience, footsteps, distant traffic and low-volume professional music. Keep speech clear.

FIXED RULES
Exactly 10 seconds; vertical 9:16; photorealistic smartphone footage; preserve the source property identity; hard cuts between separate physical areas; never invent room connections; never reveal a kitchen through the entrance unless proven; never change floor count, exterior, room dimensions, furniture or amenities; no religious imagery; no people; no CGI appearance; no floating camera; no morphing architecture; no repeated shots; no rotating captions; no oversized graphics; no distorted doors, windows or cabinets; no spelling errors; no third-party phone numbers; no generated logos.

When source information is unclear, exclude it. A simpler accurate reconstruction is always preferable to an attractive invented feature.

Disclosure for final edit: “AI visual reconstruction • Verify property during site visit.”
"""


def telegram_filename(job: dict) -> str:
    video_id = str(job.get("video_id") or "property").replace("/", "_")
    return f"{video_id}-gemini-veo-prompt.txt"
