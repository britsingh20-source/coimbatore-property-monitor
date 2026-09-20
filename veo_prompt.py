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
Moderately brisk gimbal approach along the verified local road toward the plotted development. Preserve the actual road surface, neighbouring buildings, EB poles and surroundings visible in the source.

SHOT 2 — 1.4 TO 2.8 SECONDS — LAYOUT ENTRANCE
Hard cut to the verified entrance or frontage of the layout. Show its real width, gate or boundary treatment and immediate surroundings without redesigning or beautifying it.

SHOT 3 — 2.8 TO 4.2 SECONDS — PLOTS
Hard cut to the actual vacant residential plots and visible boundary markers. Use a controlled lateral move showing the real terrain, plot arrangement and scale. Do not place a house on the plots.

SHOT 4 — 4.2 TO 5.6 SECONDS — INTERNAL ROAD
Hard cut to a verified internal road. Show an advertised road width only when its scale is supported by the source. Preserve drainage, shoulders and plot edges.

SHOT 5 — 5.6 TO 7.0 SECONDS — UTILITIES
Hard cut to visible water, electricity or other layout infrastructure. If it is not visible, use another distinct verified plot or road angle instead of inventing equipment.

SHOT 6 — 7.0 TO 8.5 SECONDS — AMENITY OR SURROUNDINGS
Hard cut to an amenity or neighbourhood feature only when visibly confirmed. Otherwise show a different genuine layout-wide angle.

SHOT 7 — 8.5 TO 10 SECONDS — FINAL LAYOUT VIEW
Hard cut to the strongest verified wide view of the plotted community. Hold the final 0.3 seconds almost motionless. No house walkthrough and no repeated angle."""
    else:
        shot_plan = """Create seven clearly different, architecturally consistent shots of approximately 1.4 seconds each. Use clean hard cuts only. All seven shots must show the same property with identical elevation, tiles, wall colours, ceiling design, built-in cabinetry, doors, windows, fixtures and room proportions.

IMPORTANT: Present the property as a clean, neutral real-estate walkthrough. Reconstruct the BUILDING, not the current occupant's personal belongings. Movable furniture and personal décor are not part of the property's architectural identity and must not be copied into the generated video.

SHOT 1 — 0 TO 1.4 SECONDS — EXTERIOR
Moderately brisk forward gimbal reveal from the verified local residential road. Preserve the visible elevation, floor count, colours, gate, windows, parking and neighbourhood. Do not redesign or enlarge the property. Ignore temporary decorations, religious/ceremonial markings, banners, people, vehicles or personal objects that are not permanent building features.

SHOT 2 — 1.4 TO 2.8 SECONDS — PARKING / PORTICO STRUCTURE, NOT THE ENTRANCE DOOR
Hard cut to the verified gate, covered parking or portico structure with a controlled lateral or diagonal move. Preserve its visible parking tiles, roof/ceiling, pillars, gate and dimensions. MANDATORY CAMERA EXCLUSION: keep the main entrance door, doorframe, lintel, doorstep and threshold completely OUTSIDE THE FRAME for the entire shot. Do not face, approach, centre, reveal or travel toward the entrance door. Do not use a straight-on doorway composition, even if the source video does. Frame toward the parking bay, gate, side wall or pillars instead. This prevents source ritual details from being copied. The visible portico floor must be plain uninterrupted tile/stone with absolutely no kolam, rangoli, chalk/paint pattern, ritual footprint, flower, garland, toran, deity symbol, religious sticker, sandal/kumkum/turmeric mark, footwear or loose household object. If the doorway cannot be excluded cleanly, replace Shot 2 with a distinct exterior, gate or parking angle where no entrance door or threshold is visible. Do not morph through the door.

SHOT 3 — 2.8 TO 4.2 SECONDS — HALL
Hard cut directly to the verified hall. Give this shot premium real-estate emphasis: bright, clean, highly polished and photorealistic while preserving the source architecture. Use a concise lateral gimbal slide showing polished flooring, windows, wall proportions, permanently installed false ceiling, fixed ceiling lighting and built-in TV panel/TV unit whenever those features are verified. INTERIOR DETAIL LOCK: preserve the verified richness of the TV wall and ceiling — layered panels, grooves/fluting, laminate/wood/stone accents, floating console, niches, profiles, cove/recessed lighting and material contrast when visible. Never simplify a detailed verified TV unit into a plain ivory slab or a detailed false ceiling into a flat/plain ceiling. Do NOT reproduce televisions, deity photos, religious images, family photos, portraits, calendars, posters, wall art, loose tables, chairs, sofas, cots, beds, mattresses or other movable personal belongings. Do not reveal another room unless that connection is clearly visible.

SHOT 4 — 4.2 TO 5.6 SECONDS — DIFFERENT VERIFIED FEATURE
Hard cut to a genuinely different permanent feature that has not appeared in Shots 1–3: prefer a verified dining area, staircase, wardrobe, bedroom, balcony, utility, ceiling-lighting detail or another architecturally useful space. STRICT NO-DUPLICATE-TV RULE: if Shot 3 shows any part of the TV panel, TV wall or TV unit, Shot 4 must not show that TV feature again—not as a wide view, close-up, reverse angle, crop, reflection or background element. A closer view of the same TV wall is a repeated shot and is forbidden. Preserve verified premium detailing after removing only prohibited personal/religious objects. Use one short upward tilt, push-in or lateral move. If no additional permanent feature is verified, show a distinct verified exterior/parking angle rather than repeating the hall or TV unit.

SHOT 5 — 5.6 TO 7.0 SECONDS — KITCHEN OR DINING
Hard cut to the verified kitchen or dining area. Present it unmistakably as a BRAND-NEW, UNOCCUPIED, NEVER-USED home: clean empty countertops, empty open niches, closed cabinets and no signs that anybody has moved in or cooked there. Show only permanent property features: built-in cabinet layout, countertop, fixed sink, backsplash/tiles, windows and room proportions. KITCHEN DETAIL / COLOUR-INDEPENDENCE LOCK: preserve every verified cabinet division, loft, drawer, handle/profile, countertop, backsplash and material/colour contrast. The TV-unit colour MUST NOT propagate to the kitchen. An ivory TV panel is not evidence for ivory kitchen cabinets, wardrobes, walls or ceilings. Reconstruct kitchen colours/materials independently from the kitchen frames in the source; if a finish cannot be verified, use restrained complementary neutral material contrast rather than making every surface the same ivory. Never flatten a visibly detailed modular kitchen into plain monochrome cabinetry. NEVER show spice bottles/jars, storage containers, tins, packets, groceries, food, utensils, vessels, pots, pans, dishes, cups, dish racks, mixer/blender, rice cooker, loose stove, water purifier, cleaning liquid, sponge, cloth, towel, waste bin, loose appliance, dining furniture, decoration or any other sign of occupation. A chimney/hob may appear only when it is permanently installed and visibly verified in the source. If the kitchen is not visible, substitute another verified architectural feature.

SHOT 6 — 7.0 TO 8.5 SECONDS — NEXT VERIFIED FEATURE
Hard cut to a verified bedroom, staircase, bathroom, balcony or parking detail. Show the permanent room/structure only. If this is a staircase shot, the staircase and surrounding architecture must remain clear and unobstructed: NEVER place or reproduce a cot, bed, mattress, chair, table, shrine, photo, idol, storage pile or any loose object under, beside or in front of the stairs. If this is a bedroom, show the verified room proportions, windows, doors and built-ins without inventing a bed or furniture. BATHROOM PRIVACY / ENCLOSURE LOCK: show a bathroom only when the source clearly verifies a logical, fully enclosed wet room with walls and a closable privacy door. Every shower, tap, toilet and floor drain must be inside that bathroom enclosure. Never place a shower or bathing fixtures in an open passage, utility, balcony, corridor, doorway, bedroom connection or uncovered area; never generate an open bathroom beside a separate toilet. Do not invent a glass partition. If bathroom enclosure or layout is ambiguous, do not show it—select a verified bedroom, staircase, balcony or parking detail instead. Use one concise push-in or lateral move and do not repeat an earlier angle.

SHOT 7 — 8.5 TO 10 SECONDS — FINAL VERIFIED FEATURE
Hard cut to one final distinct verified permanent property feature or a different exterior angle. Keep the scene clean, neutral and free of personal belongings or religious décor. Use a short reveal and keep the final 0.3 seconds almost motionless for a clean ending."""

    scale_lock = f"""PROPERTY SCALE / MARKET-REALISM LOCK — ZERO SIZE INFLATION
The verified BHK count, land area, built-up area, floor count visible in the reference, parking dimensions and price are HARD PHYSICAL SCALE CONSTRAINTS. Never upscale the property to make the video look more premium.
For this listing the governing facts are: {bhk} | land {land} | built-up {built_up} | price {price}.
The generated exterior footprint, frontage, height, portico, balcony, rooms, hall, kitchen, bedrooms and circulation must remain believable for those exact facts AND must follow the source video's visible proportions.
- A compact 2BHK / small-site / modest-price independent house must remain a compact local independent house. NEVER turn it into a grand villa, luxury bungalow, mansion, oversized duplex, broad-frontage residence or resort-style home.
- Never add a second storey, double-height facade/hall, giant balcony, oversized columns, huge lawn/setback, double-car portico, unusually wide gate/frontage or oversized rooms unless each is visibly verified in the source.
- Camera/lens choice must not fake extra size: avoid ultra-wide/fisheye views, stretched perspective, extreme low angles or framing that makes rooms/frontage appear materially larger. Prefer natural smartphone-equivalent perspective and truthful room scale.
- Price is context, not permission to redesign. Do not make a property look richer, larger or more expensive than the actual reference.
- "premium", "polished" and "photorealistic" describe IMAGE QUALITY / CLEANLINESS only, never building size or luxury class.
- Preserve verified permanent finish quality: a compact house may still show its real false ceiling, fixed lighting, built-in TV unit, cabinetry and polished flooring. Clean presentation must not erase these features.
If written facts and an AI aesthetic preference conflict, the verified source architecture and physical scale ALWAYS win.
"""

    return f"""MANDATORY OUTPUT FORMAT LOCK — READ THIS FIRST
Generate a NATIVE PORTRAIT video only: vertical 9:16 aspect ratio, ideally 1080×1920 pixels. The frame must be taller than it is wide. Never generate landscape 16:9, horizontal video, square video, a rotated landscape frame, letterboxing, pillarboxing, or a landscape clip placed inside a portrait canvas. This format requirement overrides the orientation of every source or reference.

The linked YouTube reference may be landscape. Use it only to understand the property's visual identity, then intelligently recompose every shot for a full-screen 9:16 portrait canvas. Keep the property centred with safe headroom and lower-third space. If native 9:16 output is unavailable in the current Gemini/Veo mode, do not generate a landscape substitute; instruct the user to select Portrait/9:16 mode first.

ZERO-TOLERANCE RELIGION-NEUTRAL OBJECT FILTER — PRESERVE THE ARCHITECTURE
Before planning any shot, identify prohibited personal, religious or ceremonial OBJECTS in every candidate reference angle. IMPORTANT: the presence of such an object NEVER makes the room, TV unit, false ceiling, entrance, staircase, cabinetry, wall panel or other permanent architectural feature ineligible. Remove only the prohibited object and preserve/reconstruct the verified permanent feature around it. Prohibited objects include even small, distant, blurred, partially hidden or background instances of:
- deity/god/saint photographs, idols, shrines, puja shelves or worship items;
- religious signs, symbols, stickers, tilak/sandal/kumkum/turmeric marks, ritual handprints or sacred text;
- garlands, mango-leaf torans, ceremonial flowers, lemons, coconuts or doorway worship decoration;
- kolam, rangoli, threshold drawings, ritual floor paint or chalk patterns;
- family photographs, portraits, framed people, calendars, posters, certificates or personal wall displays.

Never reproduce, blur, cover, stylise or replace a forbidden object. Instead, cleanly remove only that object and reconstruct the verified surface behind it. KEEP using the source angle when it contains important verified architecture such as a TV unit, TV wall, false ceiling, lighting design, entrance treatment, cabinetry or staircase. Religious filtering must never delete or downgrade those property features. Reconstruct only their verified geometry and finish:
- entrance/portico: plain uninterrupted floor tiles and a completely undecorated door/frame/threshold;
- hall/TV wall: blank neutral wall or empty built-in panel, with no frames, pictures, portraits, idols or display objects;
- shelves/niches: completely empty unless they are permanent architectural components;
- removed wall items: seamless continuation of the verified wall paint/panel finish;
- removed floor markings: seamless continuation of the verified floor tile/stone texture.

If a prohibited object cannot be cleanly removed with confidence, choose another angle of THE SAME VERIFIED FEATURE first. Only omit the feature when no clean verified view exists. Never omit an otherwise verified TV unit, TV wall, false ceiling, premium hall feature, fixed lighting, cabinetry or entrance merely because religious/personal content appears nearby. Do not generate a violating frame.

SECOND-SHOT PORTICO OVERRIDE
Religious and ceremonial details most often leak into the generated video when the camera copies a straight-on view of the entrance door. Therefore Shot 2 has a stricter rule than the general architecture-preservation rule: preserve the portico's permanent tiles, ceiling, pillars, gate and scale, but keep the entrance door, frame, lintel, doorstep and threshold fully outside the camera frame. The door is not required to represent the portico. Never reconstruct or clean a ritual-marked doorway in Shot 2; choose a door-free parking/portico angle instead.

REFERENCE-FIRST INSTRUCTION
Open and use this exact YouTube property video as the visual reference before generating:
{source_url}

First analyse that linked YouTube property video frame-by-frame. Base the reconstruction on the property actually shown in that video, not on a generic property or only on the written listing details. If the link cannot be opened or visually analysed, do not generate a substitute property; ask the user to retry the reference.

Identify only visually confirmed PERMANENT PROPERTY DETAILS: the exact exterior elevation, floor count, building colours and materials, gate, parking structure, entrance architecture, hall proportions, false ceiling, fixed lighting, built-in kitchen cabinetry, fixed bathroom fixtures, staircase structure, terrace, doors, windows, flooring, neighbourhood and visible connections between areas. Never infer a feature or room connection that is not clearly visible.

ARCHITECTURE-ONLY RECONSTRUCTION FILTER — MANDATORY
The source video may contain items belonging to the current owner/occupant. Treat ALL such items as visual noise, even when clearly visible. They are NOT verified property features and must NOT appear in the generated reconstruction.

Always omit and never invent: deity/religious photographs, idols, shrines, puja items, religious symbols, sandal/kumkum marks, ceremonial door markings, garlands, kolam/rangoli, family photos, portraits, calendars, posters, artwork, personal text/signage, clothes, footwear, toys, vessels, storage clutter, cots, beds, mattresses, sofas, loose chairs/tables, movable cupboards and other loose furniture or belongings.

NEW-HOME OCCUPANCY LOCK
This listing must look newly completed, vacant and ready for handover—not lived in. Kitchen counters, shelves and niches must be completely empty. Do not copy or invent spice jars, containers, groceries, food packets, vessels, utensils, cookware, countertop appliances, cleaning products, cloths, footwear, bins or household supplies anywhere. Preserve fixed cabinetry and fixtures while removing every sign of occupation.

BATHROOM LOGIC / PRIVACY LOCK
A shower or bathing area is valid only inside a clearly enclosed bathroom with walls and a closable privacy door. Never generate an exposed shower in an open passage, corridor, utility, balcony, doorway or beside a separately enclosed toilet. Never treat an ambiguous source angle as proof of an open bathroom. When the enclosure is not visually certain, omit the bathroom shot and use another verified property feature.

This exclusion rule applies EVEN IF those objects are present in the YouTube reference. Preserve the building architecture around them, but remove the personal object itself. Do not replace a removed object with another decorative object. Leave the area clean, neutral and realistic.

Never use cultural or religious styling as a way to make the property look "local", "traditional", "Indian" or "Coimbatore-style". Local realism must come only from verified architecture, street context, materials and construction details.

VERIFIED PROPERTY INFORMATION
Source: {source_url}
Reference requirement: The generated property must retain the same visible architectural identity, layout type and local setting shown in this exact source, after filtering out all personal belongings and non-architectural décor.
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

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 property walkthrough source clip at 60 fps. This clip will be slowed to 33.3% speed in VN Editor to create a smooth 30-second final video. Camera movement must be moderately brisk, stable and clear so it becomes natural after slowing. Do not reuse source frames directly. Reconstruct the property's permanent architecture using only visually confirmed architectural identity. It must resemble genuine smartphone footage recorded with a professional gimbal by a local Coimbatore property broker, not an architectural render, slideshow or AI-image animation.

INTERIOR MATERIAL / DETAIL INDEPENDENCE LOCK
Religious-object removal is OBJECT-LEVEL CLEANUP ONLY, never an interior-style reset. After removing a prohibited object, retain the verified TV unit, wall panelling, false-ceiling geometry, lighting, cabinetry, wardrobe, countertop, backsplash, flooring and architectural detailing around it. Do not turn the cleaned room into a generic plain-ivory interior.
Treat each permanent interior zone independently: TV wall colour/material does NOT determine kitchen cabinetry, bedroom wardrobe, false ceiling or other room finishes. Never propagate one ivory/white/beige finish across the whole house merely for visual consistency.
When the source clearly shows elegant layered interior work, preserve that visual complexity and finish hierarchy. "Clean/neutral" means free of personal/religious objects; it does NOT mean plain, empty, monochrome, featureless or low-detail.

REFERENCE RESEMBLANCE LOCK — 60/40
Preserve approximately 60% of the source property's verified visual identity: floor count, overall massing, frontage proportions, elevation geometry, entrance/portico position, window/door placement, roof/parapet character, parking arrangement, room proportions, false-ceiling geometry, fixed lighting, built-in TV wall/unit, kitchen cabinetry and other permanent features. The remaining approximately 40% may vary only in non-structural presentation such as neutral paint shade, clean material finish, landscaping, empty-room staging and camera composition. The 40% variation must NEVER alter floor count, convert a single-storey house into a duplex, add rooms/floors, enlarge the footprint/frontage, or erase verified interior features.

FLOOR-COUNT / BHK LAYOUT LOCK
Determine floor count from the source video before writing the shots. If the complete verified ${bhk} layout is shown on the ground floor, the generated property MUST remain a single-storey ground-floor ${bhk} home. Never infer a duplex merely because the listing uses the word villa/house. A staircase may be shown only if visibly verified, and its presence must not be interpreted as proof that bedrooms or living areas exist on another floor. No invented upper-floor facade, balcony, bedroom, hall or double-height space.

${scale_lock}

{shot_plan}

PROPERTY INFORMATION FOOTER — 0.3 TO 10 SECONDS
Display one slim, professional, completely opaque lower-third information footer continuously from 0.3 seconds until the source clip ends. It must remain upright, sharp, stationary and identical across all seven shots so it stays readable after slowing. Place it immediately above the platform watermark/safe area without covering, altering or imitating any provider provenance mark.

Use a premium deep-navy or charcoal background with high-contrast white text and one restrained gold accent. Maximum height: 14% of the frame. No rotation, animation, bouncing, perspective tilt or large caption card. Use compact separators and exactly these verified details:
“PRICE: {price}  |  LAND: {land}”
“{location}  |  SITE VISIT: {CONTACT_NUMBER}”

If price or land area is unavailable, omit that label and value completely; never display “Not specified”. Keep the location and contact number visible. Reserve enough lower safe-area space so the footer remains readable without colliding with player controls or the Gemini sparkle/provenance mark.

AUDIO
Generate no voiceover, dialogue, music, footsteps or ambience. The 10-second source clip must be silent because its speed will be reduced to 33.3% in VN Editor. Add the 30-second Tamil voiceover, music and sound effects only after slowing the visuals in VN.

FIXED RULES — HARD NEGATIVE CONSTRAINTS
Exactly 10 seconds; native 60 fps output; vertical 9:16; designed for smooth 3× slow motion; seven distinct approximately 1.4-second shots; photorealistic smartphone gimbal footage; preserve the source property's permanent architectural identity; hard cuts between separate physical areas; never invent room connections; never reveal a kitchen through the entrance unless proven; never change floor count, exterior, room dimensions, built-in cabinetry or permanent fixtures; NEVER generate religious imagery, deity photos, idols, shrines, religious symbols, ritual/ceremonial markings or worship items, even when visible in the reference; NEVER generate cots, beds, mattresses or loose furniture beside/under a staircase; NEVER invent or copy movable furniture or personal belongings; NEVER show signs of occupation in the new-home kitchen; NEVER generate an unenclosed/open shower or bathroom; no people; no CGI appearance; no floating or spinning camera; no speed ramps; no whip pans; no zoom bursts; no morphing architecture; no repeated TV unit or repeated room/feature shots; no rotating captions; no oversized graphics; one persistent professional information footer only; no distorted doors, windows or cabinets; no spelling errors; no third-party phone numbers; no generated logos.

Before rendering, perform seven mandatory audits:
1. SHOT-PLAN AUDIT: identify and remove every religious image/symbol, deity/idol/shrine, ceremonial marking, garland/toran, kolam/rangoli, family portrait, framed person, calendar, poster or personal photo. DO NOT reject the whole angle when it contains valuable verified architecture; preserve the TV unit, TV wall, false ceiling, lighting, cabinetry and other permanent features. For Shot 2 specifically, reject every composition that includes any portion of the entrance door, frame, lintel, doorstep or threshold; preserve the portico from a door-free angle.
2. FRAME-BY-FRAME AUDIT: inspect the full 10-second draft, including background walls, shelves and floors. Apply a special zero-tolerance audit from 1.4 to 2.8 seconds: the entrance door/doorframe/threshold must never enter the frame, and the portico must contain no kolam, rangoli, chalk/paint marking, ritual footprint, garland, flower, toran, symbol, sticker or ceremonial colour at any size. Reject and regenerate Shot 2 from a door-free parking/gate angle if any portion appears.
3. REPLACEMENT AUDIT: confirm every removed wall object became uninterrupted plain wall/panel finish and every removed floor/threshold marking became uninterrupted plain tile/stone. Never replace it with another picture, symbol, pattern or decoration.\n4. SCALE AUDIT: compare the draft against BHK, land area, built-up area, floor count, parking and source-video proportions. Reject any shot that makes the house, frontage, hall, portico, balcony or rooms look materially larger, grander or more luxurious than the verified property.
5. SHOT-DIVERSITY AUDIT: list the main subject of all seven shots. No permanent feature may be the main subject twice. In particular, reject the draft if the TV unit/TV wall appears in more than one shot, including crops, reverse angles, reflections or backgrounds.
6. NEW-HOME KITCHEN AUDIT: reject any kitchen frame containing spice bottles/jars, storage containers, groceries, packets, vessels, cookware, loose appliances, cleaning items, cloths, bins or any other sign of occupation. Counters and open niches must be empty.
7. BATHROOM-LOGIC AUDIT: reject any exposed shower or bathing fixture outside a clearly enclosed bathroom with walls and a closable privacy door. If the enclosure is ambiguous, replace the bathroom shot with another verified feature.

If any frame fails an audit, discard that entire shot and regenerate it from another verified architecture-only angle. Do not proceed with, export or return a violating video.

Each shot must have smooth natural motion, stable geometry, minimal motion blur and enough temporal detail to remain clean when slowed from 60 fps to a 30 fps timeline at 33.3% speed. When source information is unclear, exclude it. A simpler accurate reconstruction is always preferable to an attractive invented feature.

Disclosure for final edit: “AI visual reconstruction • Verify property during site visit.”
"""


def telegram_filename(job: dict) -> str:
    video_id = str(job.get("video_id") or "property").replace("/", "_")
    return f"{video_id}-gemini-veo-prompt.txt"
