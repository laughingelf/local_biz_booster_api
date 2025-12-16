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
    description="Backend API (FastAPI) for SEO audits and PDF-style strategy outputs.",
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
    location: str  # e.g. "Fort Worth, TX"
    industry: str  # e.g. "Lawn Care"
    main_service: str  # e.g. "Lawn mowing & yard cleanups"
    website_url: Optional[str] = None  # NEW: client's own site (optional)


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
    your_site: Optional[CompetitorResult] = None  # NEW: scanned result for client's site
    recommendations: List[str]


async def scan_site(
    client: httpx.AsyncClient,
    url: str,
    main_service_phrase: str,
) -> CompetitorResult:
    """
    Helper to fetch and analyze a single site.
    Used for both competitors and the client's own site.
    """
    try:
        resp = await client.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # --- Basic fields ---
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        meta_description = None
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            meta_description = md["content"].strip()
        else:
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
        has_faq = has_any(["faq", "frequently asked questions"])
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

        return CompetitorResult(
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
    except Exception as e:
        return CompetitorResult(url=url, error=str(e))


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_competitors(payload: AnalyzeRequest):
    """
    Local Business Booster - real competitor scan (lite version),
    now with optional comparison to the client's own site.

    For each competitor URL and (optionally) the client's URL:
      - Fetch HTML
      - Extract title + meta description
      - Detect presence of key sections (testimonials, gallery, FAQ, CTA)
      - Count how often the main service is mentioned

    Then:
      - Generate simple, actionable recommendations for the client's site.
    """
    results: List[CompetitorResult] = []
    your_site_result: Optional[CompetitorResult] = None

    main_service_phrase = payload.main_service.lower().strip()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # Scan competitors
        for url in payload.competitor_urls:
            result = await scan_site(client, url, main_service_phrase)
            results.append(result)

        # Optionally scan client's own site
        if payload.website_url:
            your_site_result = await scan_site(
                client, payload.website_url, main_service_phrase
            )

    # ---------- Build Recommendations (lite rules engine) ----------

    recommendations: List[str] = []
    valid_competitors = [r for r in results if r.error is None]

    if valid_competitors:
        # Average service keyword mentions among competitors
        avg_mentions = (
            sum(r.service_mentions for r in valid_competitors)
            / max(len(valid_competitors), 1)
        )

        if avg_mentions > 0:
            if your_site_result and your_site_result.error is None:
                if your_site_result.service_mentions < avg_mentions:
                    recommendations.append(
                        f"Your homepage mentions '{payload.main_service}' less often than competitors. Aim for at least {int(max(3, round(avg_mentions)))} mentions across headlines and body text."
                    )
                else:
                    recommendations.append(
                        f"You're using '{payload.main_service}' as frequently as top competitors. Keep that keyword focus in your main sections."
                    )
            else:
                recommendations.append(
                    f"Use the phrase '{payload.main_service}' at least {int(max(3, round(avg_mentions)))} times across your homepage (headlines + body)."
                )

        testimonial_count = sum(1 for r in valid_competitors if r.has_testimonials)
        faq_count = sum(1 for r in valid_competitors if r.has_faq)
        gallery_count = sum(1 for r in valid_competitors if r.has_gallery)
        cta_count = sum(1 for r in valid_competitors if r.has_clear_cta)

        half_or_more = max(1, len(valid_competitors) // 2)

        if testimonial_count >= half_or_more:
            if your_site_result and your_site_result.error is None and not your_site_result.has_testimonials:
                recommendations.append(
                    "Your competitors highlight testimonials or reviews, but your site does not. Add a testimonials section with real names and locations."
                )
            else:
                recommendations.append(
                    "Most competitors highlight testimonials or reviews. Make sure your testimonials section is easy to find."
                )

        if faq_count >= half_or_more:
            if your_site_result and your_site_result.error is None and not your_site_result.has_faq:
                recommendations.append(
                    "Competitors are answering questions on-site with an FAQ, but your site is missing one. Add an FAQ section for pricing, service areas, and what to expect."
                )
            else:
                recommendations.append(
                    "Competitors are answering questions with an FAQ. Make sure your FAQ covers the top objections and concerns."
                )

        if gallery_count >= half_or_more:
            if your_site_result and your_site_result.error is None and not your_site_result.has_gallery:
                recommendations.append(
                    "Competitors show their work with galleries or before/after photos, but your site doesn't. Add a simple gallery to build trust."
                )
            else:
                recommendations.append(
                    "Most competitors show their work visually. Keep your gallery updated with recent projects."
                )

        if cta_count >= half_or_more:
            if your_site_result and your_site_result.error is None and not your_site_result.has_clear_cta:
                recommendations.append(
                    "Competitors use strong 'Call Now' or 'Get a Quote' buttons above the fold. Add a clear call-to-action button near the top of your homepage."
                )
            else:
                recommendations.append(
                    "Competitors make it easy to contact or request a quote. Make sure your CTAs stand out and are above the fold."
                )

    if not recommendations:
        recommendations.append(
            "Make sure your homepage clearly states what you do, where you work, and how people can contact you within the first screen."
        )

    recommendations.append(
        "A simple one-page layout works great: hero (headline + CTA), services, testimonials, gallery, FAQ, and a final 'Book Now' section."
    )

    return AnalyzeResponse(
        competitors=results,
        your_site=your_site_result,
        recommendations=recommendations,
    )


# ---------- Digital Product Generator (One-Page Plan) ----------


class OnePageInput(BusinessInfo):
    target_audience: str  # e.g. "busy homeowners"
    tone: str  # e.g. "friendly, down-to-earth"
    primary_goal: str  # e.g. "get more calls", "book more appointments"


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
        "Final call-to-action section reminding visitors what to do next.",
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
