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

    classification = f"{property_type} {bhk} {built_up}".lower()
    is_plot_listing = (
        any(word in classification for word in ("plot", "vacant land", "residential land"))
        and not bhk
        and built_up.upper() in MISSING.union({"NOT SPECIFIED — OMIT FROM VIDEO"})
    )
    if is_plot_listing:
        shot_plan = """THIS IS A RESIDENTIAL PLOT/LAYOUT LISTING. Show only the actual land, plotted layout, roads, boundaries, infrastructure, amenities and neighbourhood confirmed by the source. Do not generate a completed house, villa elevation, portico, hall, kitchen, bedroom, bathroom or any invented interior.

Create seven distinct, consistent plot-tour shots of approximately 1.4 seconds each using clean hard cuts.

SHOT 1 — 0 TO 1.4 SECONDS — LOCATION APPROACH
Moderately brisk gimbal approach along the verified local Sulur road toward the plotted development. Preserve the actual road surface, neighbouring buildings, EB poles and surroundings visible in the source.

SHOT 2 — 1.4 TO 2.8 SECONDS — LAYOUT ENTRANCE
Hard cut to the verified entrance or frontage of the layout. Show its real width, gate or boundary treatment and immediate surroundings without redesigning or beautifying it.

SHOT 3 — 2.8 TO 4.2 SECONDS — PLOTS
Hard cut to the actual vacant residential plots and visible boundary markers. Use a controlled lateral move showing the real terrain, plot arrangement and scale. Do not place a house on the plots.

SHOT 4 — 4.2 TO 5.6 SECONDS — INTERNAL ROAD
Hard cut to a verified internal road. Show the advertised 33-ft or 40-ft road only when its scale is supported by the source. Preserve drainage, shoulders and plot edges.

SHOT 5 — 5.6 TO 7.0 SECONDS — UTILITIES
Hard cut to visible water, electricity or other layout infrastructure. If it is not visible, use another distinct verified plot or road angle instead of inventing equipment.

SHOT 6 — 7.0 TO 8.5 SECONDS — AMENITY OR SURROUNDINGS
Hard cut to a cricket turf, yoga centre or neighbourhood feature only when visibly confirmed. Otherwise show a different genuine layout-wide angle.

SHOT 7 — 8.5 TO 10 SECONDS — FINAL LAYOUT VIEW
Hard cut to the strongest verified wide view of the plotted community. Hold the final 0.3 seconds almost motionless. No house walkthrough and no repeated angle."""
    else:
        shot_plan = """Create seven clearly different, architecturally consistent shots of approximately 1.4 seconds each. Use clean hard cuts only. All seven shots must show the same property with identical elevation, tiles, wall colours, ceiling design, doors, windows, fixtures and room proportions.

SHOT 1 — 0 TO 1.4 SECONDS — EXTERIOR
Moderately brisk forward gimbal reveal from the verified local residential road. Preserve the visible elevation, floor count, colours, gate, windows, parking and neighbourhood. Do not redesign or enlarge the property.

SHOT 2 — 1.4 TO 2.8 SECONDS — PARKING OR PORTICO
Hard cut to the verified gate, covered parking or portico with a controlled forward move. Preserve its visible tiles, pillars, gate and dimensions. Keep the entrance clean and free of ceremonial markings. Do not morph through the door.

SHOT 3 — 2.8 TO 4.2 SECONDS — HALL
Hard cut directly to the verified hall. Use a concise lateral gimbal slide showing its flooring, windows, TV wall and proportions. Do not reveal another room unless that connection is clearly visible.

SHOT 4 — 4.2 TO 5.6 SECONDS — HALL DETAIL
Hard cut to a verified false ceiling, lighting, TV wall or flooring detail. Use a short upward tilt or push-in. If unavailable, use another distinct verified angle.

SHOT 5 — 5.6 TO 7.0 SECONDS — KITCHEN OR DINING
Hard cut to the verified kitchen or dining area. Show the visible cabinet layout, countertop, tiles and windows with a controlled sideways move. If it is not visible, substitute another verified feature.

SHOT 6 — 7.0 TO 8.5 SECONDS — NEXT VERIFIED FEATURE
Hard cut to a verified bedroom, staircase, bathroom, balcony or parking detail. Use one concise push-in or lateral move and do not repeat an earlier angle.

SHOT 7 — 8.5 TO 10 SECONDS — FINAL VERIFIED FEATURE
Hard cut to one final distinct verified feature or a different exterior angle. Use a short reveal and keep the final 0.3 seconds almost motionless for a clean ending."""

    return f"""MANDATORY OUTPUT FORMAT LOCK — READ THIS FIRST
Generate a NATIVE PORTRAIT video only: vertical 9:16 aspect ratio, ideally 1080×1920 pixels. The frame must be taller than it is wide. Never generate landscape 16:9, horizontal video, square video, a rotated landscape frame, letterboxing, pillarboxing, or a landscape clip placed inside a portrait canvas. This format requirement overrides the orientation of every source or reference.

The linked YouTube reference may be landscape. Use it only to understand the property's visual identity, then intelligently recompose every shot for a full-screen 9:16 portrait canvas. Keep the property centred with safe headroom and lower-third space. If native 9:16 output is unavailable in the current Gemini/Veo mode, do not generate a landscape substitute; instruct the user to select Portrait/9:16 mode first.

REFERENCE-FIRST INSTRUCTION
Open and use this exact YouTube property video as the visual reference before generating:
{source_url}

First analyse that linked YouTube property video frame-by-frame. Base the reconstruction on the property actually shown in that video, not on a generic property or only on the written listing details. If the link cannot be opened or visually analysed, do not generate a substitute property; ask the user to retry the reference.

Identify only visually confirmed details: the exact exterior elevation, floor count, building colours and materials, gate, parking, entrance, hall, false ceiling, kitchen, bedrooms, bathrooms, staircase, terrace, doors, windows, flooring, neighbourhood and visible connections between areas. Never infer a feature or room connection that is not clearly visible.

VERIFIED PROPERTY INFORMATION
Source: {source_url}
Reference requirement: The generated property must retain the same visible architectural identity, layout type and local setting shown in this exact source.
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

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 property walkthrough source clip at 60 fps. This clip will be slowed to 33.3% speed in VN Editor to create a smooth 30-second final video. Camera movement must be moderately brisk, stable and clear so it becomes natural after slowing. Do not reuse source frames directly. Reconstruct the property using only its visually confirmed architectural identity. It must resemble genuine smartphone footage recorded with a professional gimbal by a local Coimbatore property broker, not an architectural render, slideshow or AI-image animation.

{shot_plan}

PROPERTY INFORMATION FOOTER — 0.3 TO 10 SECONDS
Display one slim, professional, completely opaque lower-third information footer continuously from 0.3 seconds until the source clip ends. It must remain upright, sharp, stationary and identical across all seven shots so it stays readable after slowing. Place it immediately above the platform watermark/safe area without covering, altering or imitating any provider provenance mark.

Use a premium deep-navy or charcoal background with high-contrast white text and one restrained gold accent. Maximum height: 14% of the frame. No rotation, animation, bouncing, perspective tilt or large caption card. Use compact separators and exactly these verified details:
“PRICE: {price}  |  LAND: {land}”
“{location}  |  SITE VISIT: {CONTACT_NUMBER}”

If price or land area is unavailable, omit that label and value completely; never display “Not specified”. Keep the location and contact number visible. Reserve enough lower safe-area space so the footer remains readable without colliding with player controls or the Gemini sparkle/provenance mark.

AUDIO
Generate no voiceover, dialogue, music, footsteps or ambience. The 10-second source clip must be silent because its speed will be reduced to 33.3% in VN Editor. Add the 30-second Tamil voiceover, music and sound effects only after slowing the visuals in VN.

FIXED RULES
Exactly 10 seconds; native 60 fps output; vertical 9:16; designed for smooth 3× slow motion; seven distinct approximately 1.4-second shots; photorealistic smartphone gimbal footage; preserve the source property identity; hard cuts between separate physical areas; never invent room connections; never reveal a kitchen through the entrance unless proven; never change floor count, exterior, room dimensions, furniture or amenities; no religious imagery; no people; no CGI appearance; no floating or spinning camera; no speed ramps; no whip pans; no zoom bursts; no morphing architecture; no repeated shots; no rotating captions; no oversized graphics; one persistent professional information footer only; no distorted doors, windows or cabinets; no spelling errors; no third-party phone numbers; no generated logos.

Each shot must have smooth natural motion, stable geometry, minimal motion blur and enough temporal detail to remain clean when slowed from 60 fps to a 30 fps timeline at 33.3% speed. When source information is unclear, exclude it. A simpler accurate reconstruction is always preferable to an attractive invented feature.

Disclosure for final edit: “AI visual reconstruction • Verify property during site visit.”
"""


def telegram_filename(job: dict) -> str:
    video_id = str(job.get("video_id") or "property").replace("/", "_")
    return f"{video_id}-gemini-veo-prompt.txt"
