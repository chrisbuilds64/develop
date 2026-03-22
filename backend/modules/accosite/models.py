"""
AccoSite Builder - Domain Models

All data structures for accommodation website generation.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PropertyType(str, Enum):
    VILLA = "villa"
    GUESTHOUSE = "guesthouse"
    PENSION = "pension"
    APARTMENT = "apartment"
    HOTEL = "hotel"
    HOMESTAY = "homestay"
    OTHER = "other"


class TemplateId(str, Enum):
    TROPICAL_FRESH = "tropical-fresh"
    MODERN_MINIMAL = "modern-minimal"
    WARM_RUSTIC = "warm-rustic"
    LUXURY_DARK = "luxury-dark"


@dataclass
class PropertyInfo:
    """Step 1: Facility General Information"""
    name: str = ""
    property_type: str = "villa"
    stars: Optional[int] = None
    tagline: str = ""
    owner_name: str = ""
    email: str = ""
    phone: str = ""
    whatsapp: str = ""
    instagram: str = ""
    facebook: str = ""
    tripadvisor_url: str = ""
    google_reviews_url: str = ""
    check_in: str = "14:00"
    check_out: str = "11:00"
    year_founded: Optional[int] = None
    languages: List[str] = field(default_factory=lambda: ["en"])
    website_language: str = "en"
    about: str = ""
    history: str = ""
    policies: str = ""
    images: List[str] = field(default_factory=list)
    hero_image: str = ""


@dataclass
class RoomCategory:
    """Step 2: Room/Unit Category"""
    id: str = ""
    name: str = ""
    units: int = 1
    max_occupancy: int = 2
    size_sqm: Optional[int] = None
    bed_type: str = ""


@dataclass
class RoomDetails:
    """Step 3: Room Details (per category)"""
    category_id: str = ""
    amenities: List[str] = field(default_factory=list)
    custom_amenities: List[Dict[str, str]] = field(default_factory=list)
    short_description: str = ""
    long_description: str = ""
    images: List[str] = field(default_factory=list)
    min_stay_nights: int = 1


@dataclass
class PricingCategory:
    """Pricing for one room category"""
    category_id: str = ""
    price_high: Optional[float] = None
    price_low: Optional[float] = None
    extra_person_fee: Optional[float] = None


@dataclass
class Pricing:
    """Step 4: Pricing"""
    currency: str = "USD"
    currency_symbol: str = "$"
    show_prices: bool = True
    pricing_note: str = ""
    seasons: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[PricingCategory] = field(default_factory=list)
    taxes_included: bool = False
    tax_note: str = ""


@dataclass
class NearbyHighlight:
    """Nearby point of interest"""
    name: str = ""
    distance: str = ""
    category: str = ""


@dataclass
class Location:
    """Step 5: Location & Surroundings"""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    postal_code: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: str = ""
    google_maps_embed_url: str = ""
    about_location: str = ""
    getting_here: str = ""
    nearby: List[NearbyHighlight] = field(default_factory=list)


@dataclass
class Review:
    """Step 6: Guest Review"""
    author: str = ""
    country: str = ""
    rating: int = 5
    text: str = ""
    date: str = ""


@dataclass
class FaqEntry:
    """Step 7: FAQ Entry"""
    question: str = ""
    answer: str = ""


@dataclass
class Design:
    """Step 8: Design & Template"""
    template: str = "tropical-fresh"
    logo_path: str = ""
    color_primary: str = "#2E7D5E"
    color_accent: str = "#F4A261"
    color_background: str = "#FAFAF8"
    color_text: str = "#1A1A1A"
    font_heading: str = "Playfair Display"
    font_body: str = "Inter"
    hero_image: str = ""
    show_map: bool = True
    show_prices: bool = True
    show_reviews: bool = True
    show_faq: bool = True
    footer_text: str = ""


@dataclass
class Legal:
    """Step 9: Legal & Compliance"""
    owner_legal_name: str = ""
    owner_address: str = ""
    registration_number: str = ""
    vat_number: str = ""
    responsible_person: str = ""
    privacy_policy: str = ""
    terms: str = ""
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None


@dataclass
class Project:
    """Complete AccoSite project"""
    id: str = ""
    owner_id: str = ""
    slug: str = ""
    created_at: str = ""
    updated_at: str = ""
    current_step: int = 1
    steps_completed: Dict[int, bool] = field(
        default_factory=lambda: {i: False for i in range(1, 11)}
    )

    # Wizard data
    property_info: PropertyInfo = field(default_factory=PropertyInfo)
    room_categories: List[RoomCategory] = field(default_factory=list)
    room_details: List[RoomDetails] = field(default_factory=list)
    pricing: Pricing = field(default_factory=Pricing)
    location: Location = field(default_factory=Location)
    reviews: List[Review] = field(default_factory=list)
    faq: List[FaqEntry] = field(default_factory=list)
    design: Design = field(default_factory=Design)
    legal: Legal = field(default_factory=Legal)


# Amenity catalogue for the UI
AMENITY_CATALOGUE = {
    "connectivity": [
        {"id": "wifi", "label": "Wi-Fi (free)", "icon": "wifi"},
        {"id": "wifi_paid", "label": "Wi-Fi (paid)", "icon": "wifi"},
        {"id": "smart_tv", "label": "Smart TV", "icon": "tv"},
        {"id": "cable_tv", "label": "Cable TV", "icon": "tv"},
        {"id": "work_desk", "label": "Work Desk", "icon": "desktop"},
        {"id": "safe", "label": "Safe / Lockbox", "icon": "lock"},
    ],
    "kitchen": [
        {"id": "coffee_machine", "label": "Coffee Machine", "icon": "coffee"},
        {"id": "electric_kettle", "label": "Electric Kettle", "icon": "coffee"},
        {"id": "minibar", "label": "Minibar", "icon": "wine-glass"},
        {"id": "refrigerator", "label": "Refrigerator", "icon": "snowflake"},
        {"id": "microwave", "label": "Microwave", "icon": "utensils"},
        {"id": "kitchenette", "label": "Full Kitchen / Kitchenette", "icon": "utensils"},
        {"id": "dining_area", "label": "Dining Area", "icon": "utensils"},
    ],
    "comfort": [
        {"id": "air_conditioning", "label": "Air Conditioning", "icon": "snowflake"},
        {"id": "ceiling_fan", "label": "Ceiling Fan", "icon": "fan"},
        {"id": "private_pool", "label": "Private Pool", "icon": "water"},
        {"id": "private_jacuzzi", "label": "Private Jacuzzi", "icon": "hot-tub"},
        {"id": "balcony", "label": "Balcony / Terrace", "icon": "leaf"},
        {"id": "garden_view", "label": "Garden View", "icon": "tree"},
        {"id": "ocean_view", "label": "Ocean View", "icon": "water"},
        {"id": "rice_field_view", "label": "Rice Field View", "icon": "seedling"},
        {"id": "mountain_view", "label": "Mountain View", "icon": "mountain"},
    ],
    "bathroom": [
        {"id": "rain_shower", "label": "Rain Shower", "icon": "shower"},
        {"id": "bathtub", "label": "Bathtub", "icon": "bath"},
        {"id": "outdoor_shower", "label": "Outdoor Shower", "icon": "shower"},
        {"id": "hair_dryer", "label": "Hair Dryer", "icon": "wind"},
        {"id": "toiletries", "label": "Toiletries Provided", "icon": "pump-soap"},
        {"id": "towels", "label": "Towels & Linens", "icon": "bed"},
    ],
    "service": [
        {"id": "breakfast_included", "label": "Breakfast Included", "icon": "egg"},
        {"id": "half_board", "label": "Half Board", "icon": "utensils"},
        {"id": "daily_cleaning", "label": "Daily Housekeeping", "icon": "broom"},
        {"id": "turndown", "label": "Turn-down Service", "icon": "bed"},
        {"id": "airport_transfer", "label": "Airport Transfer", "icon": "car"},
        {"id": "laundry", "label": "Laundry Service", "icon": "shirt"},
        {"id": "private_butler", "label": "Private Butler", "icon": "user-tie"},
    ],
    "accessibility": [
        {"id": "wheelchair", "label": "Wheelchair Accessible", "icon": "wheelchair"},
        {"id": "pets_allowed", "label": "Pets Allowed", "icon": "paw"},
        {"id": "non_smoking", "label": "Non-Smoking Room", "icon": "ban-smoking"},
        {"id": "child_friendly", "label": "Child-Friendly", "icon": "baby"},
        {"id": "extra_bed", "label": "Extra Bed Available", "icon": "bed"},
    ],
}
