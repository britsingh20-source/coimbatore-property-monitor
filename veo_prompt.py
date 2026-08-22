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

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 property walkthrough source clip at 60 fps. This clip will be slowed to 33.3% speed in VN Editor to create a smooth 30-second final video. Every movement must therefore be slow, stable and continuous with enough unique visual information for slow motion. Do not reuse source frames directly. Reconstruct the property using only its visually confirmed architectural identity. It must resemble genuine smartphone footage recorded with a professional gimbal by a local Coimbatore property broker, not an architectural render, slideshow or AI-image animation.

Create five clearly different, architecturally consistent shots of approximately two seconds each. Use clean hard cuts only. All five shots must show the same property with identical elevation, floor tiles, wall colours, ceiling design, doors, windows, fixtures, daylight direction and room proportions.

SHOT 1 — 0 TO 2 SECONDS — EXTERIOR
Slow forward gimbal reveal from the verified local residential road toward the reconstructed property. Preserve the exact elevation, floor count, colours, gate, windows, parking and surrounding environment visible in the source. Include only appropriate local details visible in the source, such as neighbouring houses, EB poles, road edges, drainage and parked two-wheelers. Do not redesign, beautify or enlarge the property.

SHOT 2 — 2 TO 4 SECONDS — ENTRANCE OR PARKING
Hard cut to the verified gate, parking or portico. Use a gentle forward move toward the main entrance. Preserve the actual tiles, pillars, gate design, parking dimensions, door and exterior materials. Never morph through a closed door and never invent an exterior-to-interior connection.

SHOT 3 — 4 TO 6 SECONDS — HALL OR STRONGEST INTERIOR
Hard cut to the strongest clearly verified interior, preferably the hall when visible. Use a very slow lateral gimbal slide that clearly holds the flooring, windows, TV wall and false ceiling long enough for 3× slowing. Do not reveal a kitchen or another room through the entrance unless the source clearly proves that connection.

SHOT 4 — 6 TO 8 SECONDS — SECOND VERIFIED FEATURE
Hard cut to the next strongest verified feature mentioned or shown in the source, such as a modular kitchen, tight false-ceiling detail, bedroom, staircase, bathroom or covered parking. Match the visual to that exact feature. Use a slow push-in or sideways slide. If it is not clearly visible, replace it with another verified exterior or interior angle; never invent it.

SHOT 5 — 8 TO 10 SECONDS — THIRD VERIFIED FEATURE AND FINISH
Hard cut to another distinct, clearly verified property feature. End on a stable wide composition with at least the final 0.5 seconds almost motionless so VN can create a clean ending. Do not repeat an earlier angle. If only a few interiors are verified, finish with the exterior elevation from a genuinely different angle.

PROPERTY INFORMATION FOOTER — 0.3 TO 10 SECONDS
Display one slim, professional, completely opaque lower-third information footer continuously from 0.3 seconds until the source clip ends. It must remain upright, sharp, stationary and identical across all five shots so it stays readable after slowing. Place it immediately above the platform watermark/safe area without covering, altering or imitating any provider provenance mark.

Use a premium deep-navy or charcoal background with high-contrast white text and one restrained gold accent. Maximum height: 14% of the frame. No rotation, animation, bouncing, perspective tilt or large caption card. Use compact separators and exactly these verified details:
“PRICE: {price}  |  LAND: {land}”
“{location}  |  SITE VISIT: {CONTACT_NUMBER}”

If price or land area is unavailable, omit that label and value completely; never display “Not specified”. Keep the location and contact number visible. Reserve enough lower safe-area space so the footer remains readable without colliding with player controls or the Gemini sparkle/provenance mark.

AUDIO
Generate no voiceover, dialogue, music, footsteps or ambience. The 10-second source clip must be silent because its speed will be reduced to 33.3% in VN Editor. Add the 30-second Tamil voiceover, music and sound effects only after slowing the visuals in VN.

FIXED RULES
Exactly 10 seconds; native 60 fps output; vertical 9:16; designed for smooth 3× slow motion; five distinct approximately two-second shots; photorealistic smartphone gimbal footage; preserve the source property identity; hard cuts between separate physical areas; never invent room connections; never reveal a kitchen through the entrance unless proven; never change floor count, exterior, room dimensions, furniture or amenities; no religious imagery; no people; no CGI appearance; no floating or spinning camera; no speed ramps; no whip pans; no zoom bursts; no morphing architecture; no repeated shots; no rotating captions; no oversized graphics; one persistent professional information footer only; no distorted doors, windows or cabinets; no spelling errors; no third-party phone numbers; no generated logos.

Each shot must have smooth natural motion, stable geometry, minimal motion blur and enough temporal detail to remain clean when slowed from 60 fps to a 30 fps timeline at 33.3% speed. When source information is unclear, exclude it. A simpler accurate reconstruction is always preferable to an attractive invented feature.

Disclosure for final edit: “AI visual reconstruction • Verify property during site visit.”
"""


def telegram_filename(job: dict) -> str:
    video_id = str(job.get("video_id") or "property").replace("/", "_")
    return f"{video_id}-gemini-veo-prompt.txt"
