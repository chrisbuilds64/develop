"""
AccoSite Builder - Service Layer

AI text generation and content moderation for accommodation websites.
"""
from typing import Optional
from dataclasses import asdict

from adapters.ai.base import AIAdapter, Message
from .models import Project


# Template tone descriptors
TEMPLATE_TONES = {
    "tropical-fresh": "relaxed, inviting, nature-focused",
    "modern-minimal": "clean, precise, sophisticated",
    "warm-rustic": "warm, personal, homely",
    "luxury-dark": "exclusive, refined, understated luxury",
}


class AccoSiteService:
    """
    Business logic for AccoSite Builder.

    Handles AI text generation and content moderation.
    Uses the abstract AIAdapter interface (works with Anthropic, Mock, etc.)
    """

    def __init__(self, ai_adapter: AIAdapter):
        self.ai = ai_adapter

    def _system_prompt(self, language: str = "en", template: str = "tropical-fresh") -> str:
        tone = TEMPLATE_TONES.get(template, "warm, professional")
        return (
            f"You are a professional hospitality copywriter. Write in {language}. "
            f"Tone: {tone}. "
            f"Style: warm, professional, guest-focused. "
            f"Never invent facts. Only use the information provided. "
            f"Output only the requested text, no explanations or formatting markers."
        )

    def generate_about(self, project: Project) -> str:
        info = project.property_info
        loc = project.location
        prompt = (
            f"Property: {info.name} - {info.property_type} in "
            f"{loc.city or 'unknown city'}, {loc.country or 'unknown country'}\n"
            f"Star rating: {info.stars or 'not rated'}\n"
            f"Year founded: {info.year_founded or 'not specified'}\n"
            f"Languages: {', '.join(info.languages)}\n"
            f"Check-in: {info.check_in}, Check-out: {info.check_out}\n\n"
            f"Task: Write a compelling 'About Us' description for this property. "
            f"2-3 paragraphs, highlighting what makes it special.\n"
            f"Length: 150-250 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_history(self, project: Project) -> str:
        info = project.property_info
        prompt = (
            f"Property: {info.name} - {info.property_type}\n"
            f"Year founded: {info.year_founded or 'recently'}\n"
            f"Owner: {info.owner_name}\n\n"
            f"Task: Write a brief property history. Warm, personal tone. "
            f"If no specific history is available, write about the vision and passion "
            f"behind starting this property.\n"
            f"Length: 80-120 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_policies(self, project: Project) -> str:
        info = project.property_info
        prompt = (
            f"Property: {info.name} - {info.property_type}\n"
            f"Check-in: {info.check_in}, Check-out: {info.check_out}\n\n"
            f"Task: Write standard house rules and policies for a "
            f"{info.property_type}. Include check-in/check-out, cancellation, "
            f"smoking, noise, and general courtesy policies.\n"
            f"Length: 100-150 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_room_description(
        self, project: Project, category_id: str, length: str = "short"
    ) -> str:
        info = project.property_info
        loc = project.location
        category = None
        details = None
        for c in project.room_categories:
            if c.id == category_id:
                category = c
                break
        for d in project.room_details:
            if d.category_id == category_id:
                details = d
                break

        if not category:
            return ""

        amenities_str = ", ".join(details.amenities) if details else "standard amenities"
        if length == "short":
            task = "Write a short, enticing room description. 2-3 sentences."
            target = "40-60 words"
        else:
            task = "Write a detailed room description. 1-2 paragraphs."
            target = "100-180 words"

        prompt = (
            f"Property: {info.name} in {loc.city or ''}, {loc.country or ''}\n"
            f"Room: {category.name}\n"
            f"Size: {category.size_sqm or 'not specified'} sqm\n"
            f"Max guests: {category.max_occupancy}\n"
            f"Bed: {category.bed_type or 'not specified'}\n"
            f"Amenities: {amenities_str}\n\n"
            f"Task: {task}\n"
            f"Length: {target}"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_location_about(self, project: Project) -> str:
        info = project.property_info
        loc = project.location
        nearby = ", ".join(
            f"{h.name} ({h.distance})" for h in loc.nearby
        ) if loc.nearby else "various local attractions"

        prompt = (
            f"Property: {info.name} in {loc.city}, {loc.region}, {loc.country}\n"
            f"Nearby: {nearby}\n\n"
            f"Task: Write about the location. What makes this area special for guests? "
            f"Local culture, nature, activities.\n"
            f"Length: 100-150 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_getting_here(self, project: Project) -> str:
        loc = project.location
        prompt = (
            f"Location: {loc.address_line1}, {loc.city}, {loc.region}, {loc.country}\n\n"
            f"Task: Write practical directions for guests. Include typical transport "
            f"options (airport, taxi, private transfer). Be helpful and concise.\n"
            f"Length: 80-120 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                project.property_info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_faq(self, project: Project) -> list:
        info = project.property_info
        loc = project.location
        prompt = (
            f"Property: {info.name} - {info.property_type} in "
            f"{loc.city or ''}, {loc.country or ''}\n"
            f"Check-in: {info.check_in}, Check-out: {info.check_out}\n"
            f"Languages: {', '.join(info.languages)}\n\n"
            f"Task: Generate 6-8 FAQ entries for guests. Cover: check-in/out, "
            f"cancellation, breakfast, airport transfers, Wi-Fi, payment, pets, "
            f"booking process.\n"
            f"Format: Return as JSON array: "
            f'[{{"question": "...", "answer": "..."}}, ...]'
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ], max_tokens=1500)

        import json
        try:
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return [{"question": "What time is check-in?",
                     "answer": f"Check-in is from {info.check_in}."}]

    def generate_footer(self, project: Project) -> str:
        info = project.property_info
        prompt = (
            f"Property: {info.name}\n\n"
            f"Task: Write a brief, warm footer text for a hospitality website. "
            f"One sentence. Example style: 'Your home away from home in [location].'\n"
            f"Length: 10-20 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ], max_tokens=100)
        return response.content

    def generate_privacy_policy(self, project: Project) -> str:
        legal = project.legal
        prompt = (
            f"Business: {legal.owner_legal_name or project.property_info.name}\n"
            f"Address: {legal.owner_address}\n"
            f"Contact: {project.property_info.email}\n\n"
            f"Task: Write a minimal, GDPR-friendly privacy policy for a hospitality "
            f"website that does not use cookies or tracking. The website only has "
            f"contact forms (email, WhatsApp). Keep it simple and short.\n"
            f"Length: 100-150 words"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                project.property_info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ])
        return response.content

    def generate_seo_description(self, project: Project) -> str:
        info = project.property_info
        loc = project.location
        prompt = (
            f"Property: {info.name} - {info.property_type} in "
            f"{loc.city or ''}, {loc.country or ''}\n"
            f"Tagline: {info.tagline}\n\n"
            f"Task: Write an SEO meta description. Must be under 160 characters. "
            f"Include property name, type, and location.\n"
            f"Length: 120-155 characters"
        )
        response = self.ai.complete([
            Message(role="system", content=self._system_prompt(
                info.website_language, project.design.template
            )),
            Message(role="user", content=prompt),
        ], max_tokens=100)
        return response.content

    def moderate_text(self, text: str) -> dict:
        """Check text for prohibited content. Returns {pass: bool, reason: str}."""
        response = self.ai.complete([
            Message(
                role="system",
                content=(
                    "You are a content moderation assistant for a hospitality website builder. "
                    "Analyse the following text for: explicit sexual content, hate speech, "
                    "violent content, illegal services, discriminatory language, or "
                    "misleading/fraudulent claims. "
                    'Respond ONLY with JSON: {"pass": true} or {"pass": false, "reason": "brief reason"}'
                ),
            ),
            Message(role="user", content=f"TEXT TO REVIEW:\n{text}"),
        ], max_tokens=100)

        import json
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            return {"pass": True}
