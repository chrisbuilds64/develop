"""
AccoSite Builder - HTML Generator

Generates complete, self-contained HTML websites from project data.
4 templates: tropical-fresh, modern-minimal, warm-rustic, luxury-dark
"""
from dataclasses import asdict
from typing import Optional
import html as html_lib

from .models import Project, Design, AMENITY_CATALOGUE


# ─── Template CSS Variables ─────────────────────────────────────────────────

TEMPLATE_DEFAULTS = {
    "tropical-fresh": {
        "color_primary": "#2E7D5E",
        "color_accent": "#F4A261",
        "color_bg": "#FAFAF8",
        "color_text": "#1A1A1A",
        "color_text_muted": "#666666",
        "color_surface": "#FFFFFF",
        "font_heading": "'Playfair Display', serif",
        "font_body": "'Inter', sans-serif",
        "nav_bg": "rgba(255,255,255,0.95)",
        "hero_overlay": "linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.4) 100%)",
        "section_alt_bg": "#F0F5F2",
        "radius": "12px",
        "shadow": "0 4px 24px rgba(0,0,0,0.08)",
    },
    "modern-minimal": {
        "color_primary": "#1A1A1A",
        "color_accent": "#E63946",
        "color_bg": "#FFFFFF",
        "color_text": "#1A1A1A",
        "color_text_muted": "#888888",
        "color_surface": "#F8F8F8",
        "font_heading": "'Montserrat', sans-serif",
        "font_body": "'Inter', sans-serif",
        "nav_bg": "rgba(255,255,255,0.98)",
        "hero_overlay": "linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.5) 100%)",
        "section_alt_bg": "#F4F4F4",
        "radius": "4px",
        "shadow": "0 2px 12px rgba(0,0,0,0.06)",
    },
    "warm-rustic": {
        "color_primary": "#8B5E3C",
        "color_accent": "#D4A574",
        "color_bg": "#FAF6F1",
        "color_text": "#2C1810",
        "color_text_muted": "#7A6B5D",
        "color_surface": "#FFFFFF",
        "font_heading": "'Lora', serif",
        "font_body": "'Nunito', sans-serif",
        "nav_bg": "rgba(250,246,241,0.95)",
        "hero_overlay": "linear-gradient(180deg, rgba(44,24,16,0.1) 0%, rgba(44,24,16,0.45) 100%)",
        "section_alt_bg": "#F3EDE5",
        "radius": "8px",
        "shadow": "0 4px 20px rgba(44,24,16,0.08)",
    },
    "luxury-dark": {
        "color_primary": "#C9A96E",
        "color_accent": "#C9A96E",
        "color_bg": "#0F1923",
        "color_text": "#E8E4DF",
        "color_text_muted": "#8A9BAE",
        "color_surface": "#1A2835",
        "font_heading": "'Raleway', sans-serif",
        "font_body": "'Lato', sans-serif",
        "nav_bg": "rgba(15,25,35,0.95)",
        "hero_overlay": "linear-gradient(180deg, rgba(15,25,35,0.2) 0%, rgba(15,25,35,0.7) 100%)",
        "section_alt_bg": "#152230",
        "radius": "2px",
        "shadow": "0 4px 30px rgba(0,0,0,0.3)",
    },
}


def _e(text: str) -> str:
    """HTML-escape text."""
    return html_lib.escape(str(text)) if text else ""


def _get_amenity_label(amenity_id: str) -> str:
    """Look up amenity label from catalogue."""
    for group in AMENITY_CATALOGUE.values():
        for a in group:
            if a["id"] == amenity_id:
                return a["label"]
    return amenity_id.replace("_", " ").title()


def generate_website(project: Project, base_image_url: str = "images") -> str:
    """Generate complete HTML website from project data."""
    info = project.property_info
    design = project.design
    loc = project.location
    pricing = project.pricing
    legal = project.legal

    template_id = design.template or "tropical-fresh"
    defaults = TEMPLATE_DEFAULTS.get(template_id, TEMPLATE_DEFAULTS["tropical-fresh"])

    # Use template defaults unless operator explicitly customized colors
    # (detect by checking if color is still the Design dataclass default)
    default_design = Design()
    css_vars = {
        "color_primary": defaults["color_primary"] if design.color_primary == default_design.color_primary else design.color_primary,
        "color_accent": defaults["color_accent"] if design.color_accent == default_design.color_accent else design.color_accent,
        "color_bg": defaults["color_bg"] if design.color_background == default_design.color_background else design.color_background,
        "color_text": defaults["color_text"] if design.color_text == default_design.color_text else design.color_text,
        "color_text_muted": defaults["color_text_muted"],
        "color_surface": defaults["color_surface"],
        "font_heading": f"'{design.font_heading}', serif" if design.font_heading else defaults["font_heading"],
        "font_body": f"'{design.font_body}', sans-serif" if design.font_body else defaults["font_body"],
        "nav_bg": defaults["nav_bg"],
        "hero_overlay": defaults["hero_overlay"],
        "section_alt_bg": defaults["section_alt_bg"],
        "radius": defaults["radius"],
        "shadow": defaults["shadow"],
    }

    # Google Fonts URL
    fonts = set()
    for f in [design.font_heading, design.font_body]:
        if f:
            fonts.add(f.replace(" ", "+"))
    fonts_url = f"https://fonts.googleapis.com/css2?{'&'.join(f'family={f}:wght@400;600;700' for f in fonts)}&display=swap"

    # Build sections
    hero_image = design.hero_image or info.hero_image or ""
    hero_url = f"{base_image_url}/{hero_image}" if hero_image else ""

    nav_html = _build_nav(info, design, project)
    hero_html = _build_hero(info, hero_url, css_vars)
    about_html = _build_about(info, base_image_url)
    rooms_html = _build_rooms(project, base_image_url)
    location_html = _build_location(loc, design) if (loc.city or loc.about_location) else ""
    pricing_html = _build_pricing(pricing, project) if pricing.show_prices else ""
    reviews_html = _build_reviews(project.reviews) if design.show_reviews and project.reviews else ""
    faq_html = _build_faq(project.faq) if design.show_faq and project.faq else ""
    contact_html = _build_contact(info)
    footer_html = _build_footer(info, legal, design)

    # SEO
    seo_desc = _e(info.tagline or f"{info.name} - {info.property_type} in {loc.city}, {loc.country}")
    page_title = f"{_e(info.name)} | {_e(loc.city)} | Official Website"

    return f"""<!DOCTYPE html>
<html lang="{_e(info.website_language)}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <meta name="description" content="{seo_desc}">
    <meta name="keywords" content="{_e(loc.city)}, {_e(info.property_type)}, accommodation, {_e(loc.country)}">
    <meta property="og:title" content="{_e(info.name)}">
    <meta property="og:description" content="{seo_desc}">
    {f'<meta property="og:image" content="assets/{_e(hero_image)}">' if hero_image else ''}
    <link rel="canonical" href="">
    <link href="{fonts_url}" rel="stylesheet">
    <style>
{_build_css(css_vars, template_id)}
    </style>
</head>
<body>
    {nav_html}
    {hero_html}
    <main>
        {about_html}
        {rooms_html}
        {pricing_html}
        {location_html}
        {reviews_html}
        {faq_html}
        {contact_html}
    </main>
    {footer_html}
    <script>
{_build_js()}
    </script>
</body>
</html>"""


def _build_css(v: dict, template_id: str) -> str:
    return f"""
        :root {{
            --color-primary: {v['color_primary']};
            --color-accent: {v['color_accent']};
            --color-bg: {v['color_bg']};
            --color-text: {v['color_text']};
            --color-text-muted: {v['color_text_muted']};
            --color-surface: {v['color_surface']};
            --font-heading: {v['font_heading']};
            --font-body: {v['font_body']};
            --radius: {v['radius']};
            --shadow: {v['shadow']};
            --nav-bg: {v['nav_bg']};
            --hero-overlay: {v['hero_overlay']};
            --section-alt-bg: {v['section_alt_bg']};
        }}

        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: var(--font-body);
            color: var(--color-text);
            background: var(--color-bg);
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }}

        h1, h2, h3, h4 {{
            font-family: var(--font-heading);
            line-height: 1.2;
        }}

        img {{ max-width: 100%; height: auto; display: block; }}
        a {{ color: var(--color-primary); text-decoration: none; }}
        a:hover {{ opacity: 0.85; }}

        .container {{
            max-width: 1140px;
            margin: 0 auto;
            padding: 0 24px;
        }}

        /* ─── Navigation ─── */
        nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            background: var(--nav-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(128,128,128,0.1);
            padding: 16px 0;
            transition: all 0.3s ease;
        }}
        nav .container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        nav .logo {{
            font-family: var(--font-heading);
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--color-text);
        }}
        nav .nav-links {{
            display: flex;
            gap: 28px;
            list-style: none;
        }}
        nav .nav-links a {{
            color: var(--color-text-muted);
            font-size: 0.9rem;
            font-weight: 500;
            transition: color 0.2s;
        }}
        nav .nav-links a:hover {{ color: var(--color-primary); }}
        .nav-toggle {{ display: none; background: none; border: none; cursor: pointer; padding: 8px; }}
        .nav-toggle span {{
            display: block; width: 24px; height: 2px;
            background: var(--color-text); margin: 5px 0;
            transition: 0.3s;
        }}

        /* ─── Hero ─── */
        .hero {{
            position: relative;
            height: 85vh;
            min-height: 500px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #fff;
            overflow: hidden;
        }}
        .hero-bg {{
            position: absolute;
            inset: 0;
            background-size: cover;
            background-position: center;
            z-index: 0;
        }}
        .hero-bg::after {{
            content: '';
            position: absolute;
            inset: 0;
            background: var(--hero-overlay);
        }}
        .hero-content {{
            position: relative;
            z-index: 1;
            max-width: 700px;
            padding: 0 24px;
        }}
        .hero h1 {{
            font-size: clamp(2rem, 5vw, 3.5rem);
            margin-bottom: 16px;
            text-shadow: 0 2px 20px rgba(0,0,0,0.3);
        }}
        .hero .tagline {{
            font-size: clamp(1rem, 2vw, 1.3rem);
            opacity: 0.9;
            margin-bottom: 32px;
        }}
        .hero .cta-group {{
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }}

        /* ─── Buttons ─── */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 14px 32px;
            border-radius: var(--radius);
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            text-decoration: none;
        }}
        .btn-primary {{
            background: var(--color-primary);
            color: #fff;
        }}
        .btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}
        .btn-outline {{
            background: transparent;
            color: #fff;
            border: 2px solid rgba(255,255,255,0.7);
        }}
        .btn-outline:hover {{ background: rgba(255,255,255,0.1); }}
        .btn-accent {{
            background: var(--color-accent);
            color: #fff;
        }}

        /* ─── Sections ─── */
        section {{
            padding: 80px 0;
        }}
        section.alt {{
            background: var(--section-alt-bg);
        }}
        .section-header {{
            text-align: center;
            margin-bottom: 48px;
        }}
        .section-header h2 {{
            font-size: clamp(1.5rem, 3vw, 2.2rem);
            color: var(--color-text);
            margin-bottom: 12px;
        }}
        .section-header p {{
            color: var(--color-text-muted);
            font-size: 1.05rem;
            max-width: 600px;
            margin: 0 auto;
        }}

        /* ─── About ─── */
        .about-content {{
            max-width: 800px;
            margin: 0 auto;
            font-size: 1.05rem;
            line-height: 1.8;
        }}
        .about-content p {{ margin-bottom: 16px; }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 40px;
        }}
        .gallery img {{
            border-radius: var(--radius);
            aspect-ratio: 4/3;
            object-fit: cover;
            width: 100%;
        }}

        /* ─── Room Cards ─── */
        .rooms-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 24px;
        }}
        .room-card {{
            background: var(--color-surface);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: transform 0.2s;
        }}
        .room-card:hover {{ transform: translateY(-4px); }}
        .room-card img {{
            width: 100%;
            aspect-ratio: 16/10;
            object-fit: cover;
        }}
        .room-card-body {{
            padding: 24px;
        }}
        .room-card h3 {{
            font-size: 1.3rem;
            margin-bottom: 8px;
        }}
        .room-card .room-meta {{
            color: var(--color-text-muted);
            font-size: 0.9rem;
            margin-bottom: 12px;
        }}
        .room-card .room-meta span {{ margin-right: 16px; }}
        .room-card .amenities-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}
        .amenity-tag {{
            background: var(--section-alt-bg);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            color: var(--color-text-muted);
        }}
        .room-price {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(128,128,128,0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .room-price .price {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--color-primary);
        }}
        .room-price .per-night {{
            font-size: 0.85rem;
            color: var(--color-text-muted);
        }}

        /* ─── Location ─── */
        .location-content {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            align-items: start;
        }}
        .location-text {{ font-size: 1.05rem; line-height: 1.8; }}
        .location-text p {{ margin-bottom: 16px; }}
        .nearby-list {{ list-style: none; margin-top: 24px; }}
        .nearby-list li {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(128,128,128,0.1);
            display: flex;
            justify-content: space-between;
        }}
        .nearby-distance {{ color: var(--color-text-muted); font-size: 0.9rem; }}
        .map-container {{
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow);
        }}
        .map-container iframe {{
            width: 100%;
            height: 400px;
            border: none;
        }}

        /* ─── Reviews ─── */
        .reviews-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 24px;
        }}
        .review-card {{
            background: var(--color-surface);
            padding: 28px;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }}
        .review-stars {{ color: #F4A261; font-size: 1.1rem; margin-bottom: 12px; }}
        .review-text {{
            font-style: italic;
            line-height: 1.7;
            margin-bottom: 16px;
            color: var(--color-text);
        }}
        .review-author {{
            font-weight: 600;
            font-size: 0.9rem;
        }}
        .review-country {{
            color: var(--color-text-muted);
            font-size: 0.85rem;
        }}

        /* ─── FAQ ─── */
        .faq-list {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .faq-item {{
            border-bottom: 1px solid rgba(128,128,128,0.15);
        }}
        .faq-question {{
            padding: 20px 0;
            font-weight: 600;
            font-size: 1.05rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .faq-question::after {{
            content: '+';
            font-size: 1.5rem;
            color: var(--color-text-muted);
            transition: transform 0.2s;
        }}
        .faq-item.open .faq-question::after {{
            content: '\\2212';
        }}
        .faq-answer {{
            padding: 0 0 20px;
            color: var(--color-text-muted);
            line-height: 1.7;
            display: none;
        }}
        .faq-item.open .faq-answer {{ display: block; }}

        /* ─── Contact ─── */
        .contact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
            text-align: center;
        }}
        .contact-item {{
            background: var(--color-surface);
            padding: 32px;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }}
        .contact-item h3 {{
            margin-bottom: 8px;
            font-size: 1.1rem;
        }}
        .contact-item p {{
            color: var(--color-text-muted);
        }}
        .contact-item a {{
            color: var(--color-primary);
            font-weight: 600;
        }}

        /* ─── Footer ─── */
        footer {{
            background: {'var(--color-surface)' if template_id != 'luxury-dark' else '#0A1219'};
            padding: 40px 0;
            text-align: center;
            color: var(--color-text-muted);
            font-size: 0.9rem;
        }}
        footer a {{ color: var(--color-text-muted); }}
        footer .footer-links {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 16px;
        }}

        /* ─── Responsive ─── */
        @media (max-width: 768px) {{
            nav .nav-links {{ display: none; }}
            nav .nav-links.open {{
                display: flex;
                flex-direction: column;
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--nav-bg);
                padding: 16px 24px;
                gap: 16px;
                backdrop-filter: blur(12px);
            }}
            .nav-toggle {{ display: block; }}
            .hero {{ height: 70vh; min-height: 400px; }}
            section {{ padding: 60px 0; }}
            .location-content {{ grid-template-columns: 1fr; }}
            .rooms-grid {{ grid-template-columns: 1fr; }}
        }}
    """


def _build_js() -> str:
    return """
        // Mobile nav toggle
        document.querySelector('.nav-toggle')?.addEventListener('click', function() {
            document.querySelector('.nav-links').classList.toggle('open');
        });

        // FAQ accordion
        document.querySelectorAll('.faq-question').forEach(function(q) {
            q.addEventListener('click', function() {
                this.parentElement.classList.toggle('open');
            });
        });

        // Smooth scroll for nav links
        document.querySelectorAll('a[href^="#"]').forEach(function(a) {
            a.addEventListener('click', function(e) {
                e.preventDefault();
                var target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    document.querySelector('.nav-links')?.classList.remove('open');
                }
            });
        });

        // Navbar scroll effect
        window.addEventListener('scroll', function() {
            var nav = document.querySelector('nav');
            if (window.scrollY > 50) {
                nav.style.boxShadow = '0 2px 20px rgba(0,0,0,0.1)';
            } else {
                nav.style.boxShadow = 'none';
            }
        });
    """


def _build_nav(info, design, project) -> str:
    links = ['<li><a href="#about">About</a></li>']
    if project.room_categories:
        links.append('<li><a href="#rooms">Rooms</a></li>')
    if project.pricing.show_prices:
        links.append('<li><a href="#pricing">Pricing</a></li>')
    if project.location.city:
        links.append('<li><a href="#location">Location</a></li>')
    if design.show_reviews and project.reviews:
        links.append('<li><a href="#reviews">Reviews</a></li>')
    if design.show_faq and project.faq:
        links.append('<li><a href="#faq">FAQ</a></li>')
    links.append('<li><a href="#contact">Contact</a></li>')

    return f"""
    <nav>
        <div class="container">
            <a href="#" class="logo">{_e(info.name)}</a>
            <ul class="nav-links">
                {''.join(links)}
            </ul>
            <button class="nav-toggle" aria-label="Menu">
                <span></span><span></span><span></span>
            </button>
        </div>
    </nav>"""


def _build_hero(info, hero_url, css_vars) -> str:
    bg_style = f'background-image: url({hero_url})' if hero_url else f'background: {css_vars["color_primary"]}'
    tagline = f'<p class="tagline">{_e(info.tagline)}</p>' if info.tagline else ""

    ctas = []
    if info.whatsapp or info.phone:
        wa = info.whatsapp or info.phone
        wa_clean = wa.replace("+", "").replace(" ", "").replace("-", "")
        msg = f"Hi, I'm interested in booking at {info.name}"
        ctas.append(
            f'<a href="https://wa.me/{wa_clean}?text={msg.replace(" ", "%20")}" '
            f'class="btn btn-primary" target="_blank">WhatsApp Us</a>'
        )
    if info.email:
        ctas.append(
            f'<a href="mailto:{_e(info.email)}?subject=Booking Enquiry - {_e(info.name)}" '
            f'class="btn btn-outline">Send Email</a>'
        )

    return f"""
    <section class="hero">
        <div class="hero-bg" style="{bg_style}"></div>
        <div class="hero-content">
            <h1>{_e(info.name)}</h1>
            {tagline}
            <div class="cta-group">
                {''.join(ctas)}
            </div>
        </div>
    </section>"""


def _build_about(info, base_image_url) -> str:
    about_text = ""
    if info.about:
        paragraphs = info.about.strip().split("\n\n")
        about_text = "".join(f"<p>{_e(p.strip())}</p>" for p in paragraphs if p.strip())

    gallery_html = ""
    non_hero = [img for img in info.images if img != info.hero_image]
    if non_hero:
        if len(non_hero) <= 3:
            imgs = "".join(
                f'<img src="{base_image_url}/{_e(img)}" alt="{_e(info.name)}" loading="lazy">'
                for img in non_hero
            )
            gallery_html = f'<div class="gallery">{imgs}</div>'
        else:
            # Masonry-style: first image large, rest smaller
            first = f'<img src="{base_image_url}/{_e(non_hero[0])}" alt="{_e(info.name)}" loading="lazy" style="grid-column:span 2;aspect-ratio:16/9">'
            rest = "".join(
                f'<img src="{base_image_url}/{_e(img)}" alt="{_e(info.name)}" loading="lazy">'
                for img in non_hero[1:6]
            )
            gallery_html = f'<div class="gallery">{first}{rest}</div>'

    return f"""
    <section id="about">
        <div class="container">
            <div class="section-header">
                <h2>About {_e(info.name)}</h2>
            </div>
            <div class="about-content">
                {about_text}
            </div>
            {gallery_html}
        </div>
    </section>"""


def _build_rooms(project, base_image_url) -> str:
    if not project.room_categories:
        return ""

    cards = []
    for cat in project.room_categories:
        detail = None
        for d in project.room_details:
            if d.category_id == cat.id:
                detail = d
                break

        img_html = ""
        if detail and detail.images:
            if len(detail.images) == 1:
                img_html = f'<img src="{base_image_url}/{_e(detail.images[0])}" alt="{_e(cat.name)}" loading="lazy">'
            else:
                # Image carousel: show first image, hint at more
                img_html = f'''<div style="position:relative">
                    <img src="{base_image_url}/{_e(detail.images[0])}" alt="{_e(cat.name)}" loading="lazy">
                    <span style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.6);color:#fff;padding:2px 10px;border-radius:12px;font-size:0.75rem">
                        {len(detail.images)} photos
                    </span>
                </div>'''

        meta_parts = []
        if cat.max_occupancy:
            meta_parts.append(f"<span>Up to {cat.max_occupancy} guests</span>")
        if cat.size_sqm:
            meta_parts.append(f"<span>{cat.size_sqm} m&sup2;</span>")
        if cat.bed_type:
            meta_parts.append(f"<span>{_e(cat.bed_type)}</span>")

        amenities_html = ""
        if detail and detail.amenities:
            tags = "".join(
                f'<span class="amenity-tag">{_e(_get_amenity_label(a))}</span>'
                for a in detail.amenities[:8]
            )
            amenities_html = f'<div class="amenities-list">{tags}</div>'

        desc = _e(detail.short_description) if detail else ""

        # Price
        price_html = ""
        for pc in project.pricing.categories:
            if pc.category_id == cat.id and project.pricing.show_prices:
                price_val = pc.price_low or pc.price_high
                if price_val:
                    sym = project.pricing.currency_symbol
                    price_html = f"""
                    <div class="room-price">
                        <div>
                            <span class="price">{_e(sym)}{int(price_val)}</span>
                            <span class="per-night"> / night</span>
                        </div>
                        <a href="#contact" class="btn btn-primary" style="padding: 10px 20px; font-size: 0.85rem;">Book Now</a>
                    </div>"""
                break

        cards.append(f"""
            <div class="room-card">
                {img_html}
                <div class="room-card-body">
                    <h3>{_e(cat.name)}</h3>
                    <div class="room-meta">{''.join(meta_parts)}</div>
                    <p>{desc}</p>
                    {amenities_html}
                    {price_html}
                </div>
            </div>""")

    return f"""
    <section id="rooms" class="alt">
        <div class="container">
            <div class="section-header">
                <h2>Rooms & Accommodation</h2>
            </div>
            <div class="rooms-grid">
                {''.join(cards)}
            </div>
        </div>
    </section>"""


def _build_pricing(pricing, project) -> str:
    if not pricing.categories:
        return ""

    rows = []
    for pc in pricing.categories:
        cat_name = pc.category_id
        for c in project.room_categories:
            if c.id == pc.category_id:
                cat_name = c.name
                break

        sym = pricing.currency_symbol
        high = f"{sym}{int(pc.price_high)}" if pc.price_high else "-"
        low = f"{sym}{int(pc.price_low)}" if pc.price_low else "-"
        extra = f"{sym}{int(pc.extra_person_fee)}" if pc.extra_person_fee else "-"

        rows.append(f"""
            <tr>
                <td style="font-weight:600">{_e(cat_name)}</td>
                <td>{high}</td>
                <td>{low}</td>
                <td>{extra}</td>
            </tr>""")

    tax_note = f'<p style="margin-top:16px;color:var(--color-text-muted);font-size:0.9rem">{_e(pricing.tax_note)}</p>' if pricing.tax_note else ""

    return f"""
    <section id="pricing">
        <div class="container">
            <div class="section-header">
                <h2>Rates & Pricing</h2>
                {f'<p>{_e(pricing.pricing_note)}</p>' if pricing.pricing_note else ''}
            </div>
            <div style="max-width:700px;margin:0 auto">
                <table style="width:100%;border-collapse:collapse;text-align:left">
                    <thead>
                        <tr style="border-bottom:2px solid var(--color-primary)">
                            <th style="padding:12px 8px">Room Type</th>
                            <th style="padding:12px 8px">High Season</th>
                            <th style="padding:12px 8px">Low Season</th>
                            <th style="padding:12px 8px">Extra Person</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
                {tax_note}
            </div>
        </div>
    </section>"""


def _build_location(loc, design) -> str:
    text_html = ""
    if loc.about_location:
        paragraphs = loc.about_location.strip().split("\n\n")
        text_html = "".join(f"<p>{_e(p.strip())}</p>" for p in paragraphs if p.strip())

    nearby_html = ""
    if loc.nearby:
        items = "".join(
            f'<li><span>{_e(h.name)}</span><span class="nearby-distance">{_e(h.distance)}</span></li>'
            for h in loc.nearby
        )
        nearby_html = f'<ul class="nearby-list">{items}</ul>'

    map_html = ""
    if loc.google_maps_embed_url:
        map_html = f'<div class="map-container"><iframe src="{_e(loc.google_maps_embed_url)}" loading="lazy"></iframe></div>'
    elif loc.latitude and loc.longitude:
        osm_url = f"https://www.openstreetmap.org/export/embed.html?bbox={loc.longitude-0.01},{loc.latitude-0.01},{loc.longitude+0.01},{loc.latitude+0.01}&layer=mapnik&marker={loc.latitude},{loc.longitude}"
        map_html = f'<div class="map-container"><iframe src="{osm_url}" loading="lazy"></iframe></div>'

    right_col = map_html or nearby_html

    return f"""
    <section id="location" class="alt">
        <div class="container">
            <div class="section-header">
                <h2>Location</h2>
                <p>{_e(loc.city)}, {_e(loc.region)}, {_e(loc.country)}</p>
            </div>
            <div class="location-content">
                <div class="location-text">
                    {text_html}
                    {nearby_html if map_html else ''}
                </div>
                <div>
                    {right_col}
                </div>
            </div>
        </div>
    </section>"""


def _build_reviews(reviews) -> str:
    cards = []
    for r in reviews[:10]:
        stars = "&#9733;" * r.rating + "&#9734;" * (5 - r.rating)
        cards.append(f"""
            <div class="review-card">
                <div class="review-stars">{stars}</div>
                <p class="review-text">"{_e(r.text)}"</p>
                <p class="review-author">{_e(r.author)}</p>
                <p class="review-country">{_e(r.country)}{f' &middot; {_e(r.date)}' if r.date else ''}</p>
            </div>""")

    return f"""
    <section id="reviews">
        <div class="container">
            <div class="section-header">
                <h2>Guest Reviews</h2>
            </div>
            <div class="reviews-grid">
                {''.join(cards)}
            </div>
        </div>
    </section>"""


def _build_faq(faq_entries) -> str:
    items = []
    for f in faq_entries:
        items.append(f"""
            <div class="faq-item">
                <div class="faq-question">{_e(f.question)}</div>
                <div class="faq-answer">{_e(f.answer)}</div>
            </div>""")

    return f"""
    <section id="faq" class="alt">
        <div class="container">
            <div class="section-header">
                <h2>Frequently Asked Questions</h2>
            </div>
            <div class="faq-list">
                {''.join(items)}
            </div>
        </div>
    </section>"""


def _build_contact(info) -> str:
    items = []

    if info.whatsapp or info.phone:
        wa = info.whatsapp or info.phone
        wa_clean = wa.replace("+", "").replace(" ", "").replace("-", "")
        items.append(f"""
            <div class="contact-item">
                <h3>WhatsApp</h3>
                <p><a href="https://wa.me/{wa_clean}" target="_blank">{_e(wa)}</a></p>
            </div>""")

    if info.email:
        items.append(f"""
            <div class="contact-item">
                <h3>Email</h3>
                <p><a href="mailto:{_e(info.email)}">{_e(info.email)}</a></p>
            </div>""")

    if info.phone:
        items.append(f"""
            <div class="contact-item">
                <h3>Phone</h3>
                <p><a href="tel:{_e(info.phone)}">{_e(info.phone)}</a></p>
            </div>""")

    social = []
    if info.instagram:
        social.append(f'<a href="https://instagram.com/{_e(info.instagram)}" target="_blank">Instagram</a>')
    if info.facebook:
        social.append(f'<a href="{_e(info.facebook)}" target="_blank">Facebook</a>')
    if info.tripadvisor_url:
        social.append(f'<a href="{_e(info.tripadvisor_url)}" target="_blank">TripAdvisor</a>')

    if social:
        items.append(f"""
            <div class="contact-item">
                <h3>Follow Us</h3>
                <p>{' &middot; '.join(social)}</p>
            </div>""")

    return f"""
    <section id="contact">
        <div class="container">
            <div class="section-header">
                <h2>Get in Touch</h2>
                <p>We would love to hear from you</p>
            </div>
            <div class="contact-grid">
                {''.join(items)}
            </div>
        </div>
    </section>"""


def _build_footer(info, legal, design) -> str:
    footer_text = design.footer_text or f"&copy; {info.name}. All rights reserved."
    links = []
    if legal.privacy_policy:
        links.append('<a href="#privacy">Privacy Policy</a>')
    if legal.terms:
        links.append('<a href="#terms">Terms</a>')
    if legal.owner_legal_name:
        links.append('<a href="#imprint">Imprint</a>')

    links_html = f'<div class="footer-links">{"".join(links)}</div>' if links else ""

    return f"""
    <footer>
        <div class="container">
            <p>{footer_text}</p>
            {links_html}
        </div>
    </footer>"""
