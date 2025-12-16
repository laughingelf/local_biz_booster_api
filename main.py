# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup


app = FastAPI(
    title="Local Business Booster & Digital Product Generator",
    version="0.1.0",
    description="Backend API (FastAPI) for SEO audits and PDF-style strategy outputs."
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",   
    "https://ghoststackdesigns.com",
    "https://www.ghoststackdesigns.com",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Shared Models ----------

class BusinessInfo(BaseModel):
    business_name: str
    location: str          # e.g. "Fort Worth, TX"
    industry: str          # e.g. "Lawn Care"
    main_service: str      # e.g. "Lawn mowing & yard cleanups"


# ---------- Local Business Booster ----------

class AnalyzeRequest(BusinessInfo):
    competitor_urls: List[str]


class CompetitorResult(BaseModel):
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    has_testimonials: bool = False
    has_gallery: bool = False
    has_faq: bool = False
    has_clear_cta: bool = False
    service_mentions: int = 0
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    competitors: List[CompetitorResult]
    recommendations: List[str]


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_competitors(payload: AnalyzeRequest):
    """
    Local Business Booster - real competitor scan (lite version).

    For each competitor URL:
      - Fetch HTML
      - Extract title + meta description
      - Detect presence of key sections (testimonials, gallery, FAQ, CTA)
      - Count how often the main service is mentioned
    Then:
      - Generate simple, actionable recommendations for the client's site.
    """
    results: List[CompetitorResult] = []

    # We'll reuse this lowercased service phrase for counting
    main_service_phrase = payload.main_service.lower().strip()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in payload.competitor_urls:
            try:
                resp = await client.get(url)
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                # --- Basic fields ---
                title = soup.title.string.strip() if soup.title and soup.title.string else None

                meta_description = None
                # Standard meta description
                md = soup.find("meta", attrs={"name": "description"})
                if md and md.get("content"):
                    meta_description = md["content"].strip()
                else:
                    # fallback: some sites use og:description
                    og = soup.find("meta", attrs={"property": "og:description"})
                    if og and og.get("content"):
                        meta_description = og["content"].strip()

                # --- Full text (for simple keyword/section detection) ---
                text = soup.get_text(separator=" ", strip=True).lower()

                def has_any(keywords: List[str]) -> bool:
                    return any(k in text for k in keywords)

                has_testimonials = has_any(
                    ["testimonial", "testimonials", "what our customers say", "reviews", "review"]
                )
                has_gallery = has_any(
                    ["gallery", "our work", "portfolio", "before and after"]
                )
                has_faq = has_any(
                    ["faq", "frequently asked questions"]
                )
                has_clear_cta = has_any(
                    [
                        "call now",
                        "get a quote",
                        "get a free quote",
                        "free estimate",
                        "book now",
                        "schedule now",
                        "request a quote",
                        "request a call",
                    ]
                )

                service_mentions = 0
                if main_service_phrase:
                    service_mentions = text.count(main_service_phrase)

                result = CompetitorResult(
                    url=url,
                    title=title,
                    meta_description=meta_description,
                    has_testimonials=has_testimonials,
                    has_gallery=has_gallery,
                    has_faq=has_faq,
                    has_clear_cta=has_clear_cta,
                    service_mentions=service_mentions,
                    error=None,
                )
                results.append(result)

            except Exception as e:
                # If anything goes wrong for this URL, capture the error but don't blow up the whole response
                results.append(
                    CompetitorResult(
                        url=url,
                        error=str(e),
                    )
                )

    # ---------- Build Recommendations (lite rules engine) ----------

    recommendations: List[str] = []

    # Only consider competitors that didn't error out
    valid_competitors = [r for r in results if r.error is None]

    if valid_competitors:
        # Average service keyword mentions
        avg_mentions = (
            sum(r.service_mentions for r in valid_competitors) / max(len(valid_competitors), 1)
        )

        if avg_mentions > 0:
            recommendations.append(
                f"Use the phrase '{payload.main_service}' at least {int(max(3, round(avg_mentions)))} times across your homepage (headlines + body)."
            )

        # Section prevalence among competitors
        testimonial_count = sum(1 for r in valid_competitors if r.has_testimonials)
        faq_count = sum(1 for r in valid_competitors if r.has_faq)
        gallery_count = sum(1 for r in valid_competitors if r.has_gallery)
        cta_count = sum(1 for r in valid_competitors if r.has_clear_cta)

        half_or_more = max(1, len(valid_competitors) // 2)

        if testimonial_count >= half_or_more:
            recommendations.append(
                "Most of your competitors highlight testimonials or reviews. Add a clear testimonials section with real names and locations."
            )

        if faq_count >= half_or_more:
            recommendations.append(
                "Competitors are answering questions directly on the site. Add an FAQ section to handle pricing, service areas, and what to expect."
            )

        if gallery_count >= half_or_more:
            recommendations.append(
                "Competitors are showing their work. Add a simple before/after gallery or recent projects section to build trust."
            )

        if cta_count >= half_or_more:
            recommendations.append(
                "Many competitors are using strong 'Call Now' or 'Get a Quote' buttons. Make sure you have a clear call-to-action visible above the fold."
            )

    # Always include at least one generic but useful recommendation
    if not recommendations:
        recommendations.append(
            "Make sure your homepage clearly states what you do, where you work, and how people can contact you within the first screen."
        )

    # Add a GhostStack-flavored CTA recommendation
    recommendations.append(
        "Consider a simple one-page layout: hero (headline + CTA), services, testimonials, gallery, FAQ, and a final 'Book Now' section."
    )

    return AnalyzeResponse(
        competitors=results,
        recommendations=recommendations,
    )



# ---------- Digital Product Generator (One-Page Plan) ----------

class OnePageInput(BusinessInfo):
    target_audience: str   # e.g. "busy homeowners"
    tone: str              # e.g. "friendly, down-to-earth"
    primary_goal: str      # e.g. "get more calls", "book more appointments"


class OnePagePlan(BaseModel):
    hero_headline: str
    hero_subheadline: str
    primary_cta: str
    secondary_cta: str
    about_bullets: List[str]
    sections: List[str]


@app.post("/generate/one-page", response_model=OnePagePlan)
def generate_one_page_plan(data: OnePageInput):
    """
    MVP of your Digital Product Generator.
    Returns a structured plan you can render in your frontend or later turn into a PDF.
    """
    hero_headline = f"{data.main_service} in {data.location} for {data.target_audience}"
    hero_subheadline = (
        f"{data.business_name} provides {data.industry.lower()} services for "
        f"{data.target_audience.lower()}, making it easier to {data.primary_goal.lower()}."
    )

    about_bullets = [
        f"Locally owned and serving {data.location}.",
        f"Focused on {data.target_audience.lower()} who want reliable {data.industry.lower()} services.",
        f"Specializing in {data.main_service.lower()} with a {data.tone} style.",
    ]

    sections = [
        "Hero section with strong headline, subheadline, and call-to-action buttons.",
        "About section telling your story and why you care about your customers.",
        "Services section highlighting 3–5 main services with benefits.",
        "Testimonials section to build trust.",
        "Simple contact / quote form with phone and email.",
        "Final call-to-action section reminding visitors what to do next."
    ]

    return OnePagePlan(
        hero_headline=hero_headline,
        hero_subheadline=hero_subheadline,
        primary_cta=f"Get Your {data.main_service} Today",
        secondary_cta="Request a Free Quote",
        about_bullets=about_bullets,
        sections=sections,
    )


# ---------- Basic Health Check ----------

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API is running"}
