# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

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
    MVP version for Local Business Booster.
    Right now this is a stub that just echoes back basic structure.
    Next step: add real scraping and analysis.
    """
    # For now, fake some results so you can test the frontend and deployment.
    results: List[CompetitorResult] = []

    for url in payload.competitor_urls:
        results.append(
            CompetitorResult(
                url=url,
                title=f"Placeholder title for {url}",
                meta_description="Sample meta description (replace with real scraping later).",
                has_testimonials=True,
                has_gallery=False,
                has_faq=True,
                has_clear_cta=True,
                service_mentions=5,
            )
        )

    recommendations = [
        f"Use the phrase '{payload.main_service}' more in your headings and body text.",
        "Add a testimonials section if you don't already have one.",
        "Make sure you have a clear 'Call Now' or 'Get a Quote' button above the fold."
    ]

    return AnalyzeResponse(
        competitors=results,
        recommendations=recommendations
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
