"""
AccoSite Builder - Project Repository

File-based project storage. Each project is a JSON file on disk.
MVP: simple JSON files. No database needed.
"""
import json
import os
import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import asdict

from .models import Project, PropertyInfo, RoomCategory, RoomDetails
from .models import Pricing, PricingCategory, Location, NearbyHighlight
from .models import Review, FaqEntry, Design, Legal


SECTION_MAP = {
    "property": "property_info",
    "rooms": "room_categories",
    "room_details": "room_details",
    "pricing": "pricing",
    "location": "location",
    "reviews": "reviews",
    "faq": "faq",
    "design": "design",
    "legal": "legal",
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60] or "untitled"


class ProjectRepository:
    """
    File-based storage for AccoSite projects.

    Storage layout:
        {base_dir}/{owner_id}/{project_id}/project.json
        {base_dir}/{owner_id}/{project_id}/images/
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _project_dir(self, owner_id: str, project_id: str) -> str:
        return os.path.join(self.base_dir, owner_id, project_id)

    def _project_file(self, owner_id: str, project_id: str) -> str:
        return os.path.join(self._project_dir(owner_id, project_id), "project.json")

    def _images_dir(self, owner_id: str, project_id: str) -> str:
        return os.path.join(self._project_dir(owner_id, project_id), "images")

    def _save_json(self, owner_id: str, project_id: str, data: dict):
        project_dir = self._project_dir(owner_id, project_id)
        os.makedirs(project_dir, exist_ok=True)
        with open(self._project_file(owner_id, project_id), "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_json(self, owner_id: str, project_id: str) -> Optional[dict]:
        filepath = self._project_file(owner_id, project_id)
        if not os.path.exists(filepath):
            return None
        with open(filepath) as f:
            return json.load(f)

    def create(self, owner_id: str, name: str) -> Project:
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        slug = _slugify(name)

        project = Project(
            id=project_id,
            owner_id=owner_id,
            slug=slug,
            created_at=now,
            updated_at=now,
        )
        project.property_info.name = name

        self._save_json(owner_id, project_id, asdict(project))
        os.makedirs(self._images_dir(owner_id, project_id), exist_ok=True)

        return project

    def get(self, owner_id: str, project_id: str) -> Optional[Project]:
        data = self._load_json(owner_id, project_id)
        if not data:
            return None
        return self._dict_to_project(data)

    def list_projects(self, owner_id: str) -> List[dict]:
        owner_dir = os.path.join(self.base_dir, owner_id)
        if not os.path.exists(owner_dir):
            return []

        projects = []
        for project_id in os.listdir(owner_dir):
            data = self._load_json(owner_id, project_id)
            if data:
                projects.append({
                    "id": data["id"],
                    "slug": data.get("slug", ""),
                    "name": data.get("property_info", {}).get("name", "Untitled"),
                    "current_step": data.get("current_step", 1),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "template": data.get("design", {}).get("template", "tropical-fresh"),
                })
        return sorted(projects, key=lambda p: p["updated_at"], reverse=True)

    def save_section(
        self, owner_id: str, project_id: str, section: str, data: dict
    ) -> bool:
        project_data = self._load_json(owner_id, project_id)
        if not project_data:
            return False

        field_name = SECTION_MAP.get(section, section)
        # For dict sections: merge with existing data (don't lose fields)
        # For list sections (rooms, room_details, reviews, faq): replace entirely
        if isinstance(data, dict) and isinstance(project_data.get(field_name), dict):
            project_data[field_name].update(data)
        else:
            project_data[field_name] = data
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_json(owner_id, project_id, project_data)
        return True

    def update_step(
        self, owner_id: str, project_id: str, step: int, completed: bool = True
    ) -> bool:
        project_data = self._load_json(owner_id, project_id)
        if not project_data:
            return False

        project_data["current_step"] = step
        if "steps_completed" not in project_data:
            project_data["steps_completed"] = {}
        project_data["steps_completed"][str(step)] = completed
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_json(owner_id, project_id, project_data)
        return True

    def delete(self, owner_id: str, project_id: str) -> bool:
        import shutil
        project_dir = self._project_dir(owner_id, project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
            return True
        return False

    def get_images_dir(self, owner_id: str, project_id: str) -> str:
        images_dir = self._images_dir(owner_id, project_id)
        os.makedirs(images_dir, exist_ok=True)
        return images_dir

    def _dict_to_project(self, data: dict) -> Project:
        """Convert dict back to Project dataclass."""
        project = Project(
            id=data.get("id", ""),
            owner_id=data.get("owner_id", ""),
            slug=data.get("slug", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            current_step=data.get("current_step", 1),
            steps_completed=data.get("steps_completed", {}),
        )

        pi = data.get("property_info", {})
        project.property_info = PropertyInfo(**{
            k: v for k, v in pi.items()
            if k in PropertyInfo.__dataclass_fields__
        })

        cats = data.get("room_categories", [])
        project.room_categories = [
            RoomCategory(**{k: v for k, v in c.items()
                          if k in RoomCategory.__dataclass_fields__})
            for c in cats
        ]

        details = data.get("room_details", [])
        project.room_details = [
            RoomDetails(**{k: v for k, v in d.items()
                          if k in RoomDetails.__dataclass_fields__})
            for d in details
        ]

        pr = data.get("pricing", {})
        pricing_cats = pr.pop("categories", []) if isinstance(pr, dict) else []
        project.pricing = Pricing(**{
            k: v for k, v in pr.items()
            if k in Pricing.__dataclass_fields__ and k != "categories"
        })
        project.pricing.categories = [
            PricingCategory(**{k: v for k, v in pc.items()
                              if k in PricingCategory.__dataclass_fields__})
            for pc in pricing_cats
        ]

        loc = data.get("location", {})
        nearby_raw = loc.pop("nearby", []) if isinstance(loc, dict) else []
        project.location = Location(**{
            k: v for k, v in loc.items()
            if k in Location.__dataclass_fields__ and k != "nearby"
        })
        project.location.nearby = [
            NearbyHighlight(**{k: v for k, v in n.items()
                              if k in NearbyHighlight.__dataclass_fields__})
            for n in nearby_raw
        ]

        revs = data.get("reviews", [])
        project.reviews = [
            Review(**{k: v for k, v in r.items()
                     if k in Review.__dataclass_fields__})
            for r in revs
        ]

        faqs = data.get("faq", [])
        project.faq = [
            FaqEntry(**{k: v for k, v in f.items()
                       if k in FaqEntry.__dataclass_fields__})
            for f in faqs
        ]

        des = data.get("design", {})
        project.design = Design(**{
            k: v for k, v in des.items()
            if k in Design.__dataclass_fields__
        })

        leg = data.get("legal", {})
        project.legal = Legal(**{
            k: v for k, v in leg.items()
            if k in Legal.__dataclass_fields__
        })

        return project
