# Dynamic Discovery Architecture

Aibros must not depend on a fixed list of AI companies or free tools.

## Two expanding registries

### Source Registry

Stores official company blogs, changelogs, documentation, GitHub organizations,
Hugging Face organizations, RSS/Atom feeds, YouTube release channels and research
publishers.

Sources move through:

`candidate -> quarantined -> verified -> trusted -> degraded -> retired`

A newly discovered source never becomes publishable merely because another
creator or directory linked to it. Promotion requires an official domain,
identity match, recent original content, valid TLS, stable retrieval and at
least one independently verifiable product/release.

### Tool Catalogue

Stores every free/open-source method with:

- canonical tool identity and aliases;
- official URL and repository;
- first seen, last checked and next check;
- free type: open source, completely free, free tier, credits or trial;
- card, watermark, export, regional and commercial-use restrictions;
- operating system, browser/mobile availability and hardware requirements;
- replacement category and paid alternatives;
- evidence snapshots and change history.

Tools move through:

`candidate -> verified_free -> changed -> review_required -> unavailable -> archived`

## Continuous expansion

Every discovery run also extracts new organizations, domains, repositories and
products mentioned by already trusted sources. Unknown entities enter the
candidate queue. The system checks official ownership and evidence before
promotion.

## Reverification

- breaking announcements: every 6 hours for 48 hours;
- free tiers and browser tools: every 7 days;
- open-source repositories: every 14 days;
- trials and promotional credits: every 24 hours;
- unavailable tools: every 30 days;
- every item: immediately when pricing, terms, licence or documentation changes.

If an old Aibros video claims a tool is free and the catalogue later detects a
change, the tool is marked `changed`; it cannot be reused until reviewed.

## Discovery is not evidence

Directories, newsletters, social posts and competitor channels are discovery
signals only. Publishable claims must be supported by an official company page,
official repository, official documentation or another authoritative primary
source.

## Diversity controls

The daily selector prevents one large company from dominating:

- no more than one topic per company per day unless it is major breaking news;
- reserve at least 30% of weekly slots for newly discovered companies;
- reserve at least 30% for open-source/free methods;
- do not repeat a tool within 30 days unless it materially changed;
- track categories so image/video/chatbot tools do not crowd out agents,
  research, coding, audio, productivity and Indian-language AI.
