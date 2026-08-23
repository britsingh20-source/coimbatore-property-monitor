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
    facts = _value(job.get("verified_facts"), "Use only facts confirmed in the source video")
    source_url = _value(job.get("source_url"), "Source video supplied separately")

    return f"""Open and analyse this public YouTube property-tour video directly as the architectural reference: {source_url}

Study the property frame-by-frame and identify only the visible exterior elevation, floor count, colours, materials, gate, parking, entrance, hall, false ceiling, kitchen, bedrooms, bathrooms, staircase, terrace, doors, windows, flooring, neighbourhood and verified room connections. Use the source only to understand the property architecture. Generate completely new footage; do not reproduce source frames, presenters, people, faces, speech, music, logos, watermarks, captions or channel branding. Never infer a feature or room connection that is not clearly visible.

VERIFIED PROPERTY INFORMATION
Source reference: {source_url}
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

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 property walkthrough source clip at 60 fps. This clip will be slowed to 33.3% speed in VN Editor to create a smooth 30-second final video. Source-camera movement must be moderately fast, stable and continuous—approximately three times the desired final viewing speed—so it becomes natural and premium after slowing. Avoid motion blur and preserve clear geometry in every frame. Do not reuse source frames directly. Reconstruct the property using only its visually confirmed architectural identity. It must resemble genuine smartphone footage recorded with a professional gimbal by a local Coimbatore property broker, not an architectural render, slideshow or AI-image animation.

Create seven clearly different, architecturally consistent shots of approximately 1.4 seconds each. Use clean hard cuts only. All seven shots must show the same property with identical elevation, floor tiles, wall colours, ceiling design, doors, windows, fixtures, daylight direction and room proportions. Each source shot should contain one concise, moderately brisk gimbal move that becomes a smooth 4.0–4.5 second shot after slowing to 33.3%.

SHOT 1 — 0 TO 1.4 SECONDS — EXTERIOR ESTABLISHING
Moderately brisk forward gimbal reveal from the verified local residential road toward the reconstructed property. Preserve the exact elevation, floor count, colours, gate, windows, parking and surrounding environment visible in the source. Include only appropriate local details visible in the source, such as neighbouring houses, EB poles, road edges, drainage and parked two-wheelers. Do not redesign, beautify or enlarge the property.

SHOT 2 — 1.4 TO 2.8 SECONDS — GATE, PARKING OR PORTICO
Hard cut to the verified gate, parking or portico. Use a controlled forward move toward the main entrance. Preserve the architectural door style, tiles, pillars, gate design, parking dimensions and exterior materials, but present the entrance as newly completed, professionally cleaned and religion-neutral. The door, frame, lintel, steps and threshold must be completely free of sandalwood paste, santhanam, kumkum, turmeric, vermilion, religious dots, handprints, deity stickers, Om or swastika symbols, garlands, flowers, mango leaves, lemons, coconuts, kolam/rangoli, ritual paint and ceremonial decorations. Remove such source details instead of reproducing them. Never morph through a closed door and never invent an exterior-to-interior connection.

SHOT 3 — 2.8 TO 4.2 SECONDS — HALL
Hard cut directly inside the clearly verified hall. Use a controlled lateral gimbal slide showing flooring, windows, TV wall and room proportions. Do not reveal the kitchen or another room unless the source clearly proves that connection.

SHOT 4 — 4.2 TO 5.6 SECONDS — FALSE CEILING OR HALL DETAIL
Hard cut to a tighter verified hall feature, preferably the false ceiling, lighting, TV wall or premium flooring. Use a short upward tilt, push-in or sideways slide. If no such detail is verified, use another genuinely different hall or exterior angle.

SHOT 5 — 5.6 TO 7.0 SECONDS — KITCHEN OR DINING
Hard cut to the verified modular kitchen or dining space. Use a controlled sideways move that clearly shows cabinet layout, countertop, tiles and windows. Never invent a kitchen or alter its materials; when the kitchen is not visible in the source, substitute another verified feature.

SHOT 6 — 7.0 TO 8.5 SECONDS — BEDROOM, STAIRCASE OR PARKING DETAIL
Hard cut to the next strongest verified feature: bedroom, staircase, bathroom, balcony, covered parking or another distinct interior. Match only what is visibly confirmed. Use one concise push-in or lateral move; never repeat an earlier angle.

SHOT 7 — 8.5 TO 10 SECONDS — FINAL VERIFIED FEATURE
Hard cut to one final distinct verified feature or a different exterior elevation angle. Use a short controlled reveal, then hold the final 0.3 seconds nearly motionless in the source so the slowed VN edit has a clean ending. Never repeat an earlier shot.

PROPERTY INFORMATION FOOTER — 0.3 TO 10 SECONDS
Display one slim, professional, completely opaque lower-third information footer continuously from 0.3 seconds until the source clip ends. It must remain upright, sharp, stationary and identical across all seven shots so it stays readable after slowing. Place it immediately above the platform watermark/safe area without covering, altering or imitating any provider provenance mark.

Use a premium deep-navy or charcoal background with high-contrast white text and one restrained gold accent. Maximum height: 14% of the frame. No rotation, animation, bouncing, perspective tilt or large caption card. Use compact separators and exactly these verified details:
“PRICE: {price}  |  LAND: {land}”
“{location}  |  SITE VISIT: {CONTACT_NUMBER}”

If price or land area is unavailable, omit that label and value completely; never display “Not specified”. Keep the location and contact number visible. Reserve enough lower safe-area space so the footer remains readable without colliding with player controls or the Gemini sparkle/provenance mark.

AUDIO
Generate no voiceover, dialogue, music, footsteps or ambience. The 10-second source clip must be silent because its speed will be reduced to 33.3% in VN Editor. Add the 30-second Tamil voiceover, music and sound effects only after slowing the visuals in VN.

FIXED RULES
Exactly 10 seconds; native 60 fps output; vertical 9:16; designed for smooth 3× slow motion; seven distinct approximately 1.4-second shots; photorealistic smartphone gimbal footage; preserve the source property identity while removing every religious or ceremonial mark; hard cuts between separate physical areas; never invent room connections; never reveal a kitchen through the entrance unless proven; never change floor count, exterior, room dimensions, furniture or amenities; all entrances must look newly cleaned and religion-neutral; no santhanam, sandal paste, kumkum, turmeric, vermilion, religious dots, handprints, deity stickers, Om, swastika, cross, crescent, garlands, flowers, mango leaves, lemons, coconuts, kolam/rangoli, ritual threshold paint, ceremonial decorations or religious carvings; no people; no CGI appearance; no floating or spinning camera; no speed ramps; no whip pans; no zoom bursts; no morphing architecture; no repeated shots; no rotating captions; no oversized graphics; one persistent professional information footer only; no distorted doors, windows or cabinets; no spelling errors; no third-party phone numbers; no generated logos.

Each shot must have smooth natural motion, stable geometry, minimal motion blur and enough temporal detail to remain clean when slowed from 60 fps to a 30 fps timeline at 33.3% speed. When source information is unclear, exclude it. A simpler accurate reconstruction is always preferable to an attractive invented feature.

Disclosure for final edit: “AI visual reconstruction • Verify property during site visit.”
"""


def telegram_filename(job: dict) -> str:
    video_id = str(job.get("video_id") or "property").replace("/", "_")
    return f"{video_id}-gemini-veo-prompt.txt"
