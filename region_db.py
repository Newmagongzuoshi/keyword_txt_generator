import json
from pathlib import Path

from config import LEVEL_PROVINCE, LEVEL_CITY, LEVEL_COUNTY, LEVEL_TOWN, LEVEL_VILLAGE


class RegionDatabase:
    def __init__(self):
        self.regions = []
        self.region_by_id = {}
        self.alias_index = {}
        self.level_index = {
            LEVEL_PROVINCE: [],
            LEVEL_CITY: [],
            LEVEL_COUNTY: [],
            LEVEL_TOWN: [],
            LEVEL_VILLAGE: [],
        }
        self.parent_children_index = {}

    @classmethod
    def load(cls, path="region_db.json"):
        db_path = Path(path)
        if not db_path.is_absolute():
            db_path = Path(__file__).parent / path
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        db = cls()
        db.regions = data
        db._build_indexes()
        return db

    def _build_indexes(self):
        for region in self.regions:
            rid = region["id"]
            self.region_by_id[rid] = region
            level = region["level"]
            if level in self.level_index:
                self.level_index[level].append(region)

            names = set()
            names.add(region["name"])
            names.add(region["short_name"])
            for alias in region.get("aliases", []):
                names.add(alias)

            for name in names:
                name = name.strip()
                if not name:
                    continue
                if name not in self.alias_index:
                    self.alias_index[name] = []
                self.alias_index[name].append(region)

            parent_id = region.get("parent_id", "")
            if parent_id:
                if parent_id not in self.parent_children_index:
                    self.parent_children_index[parent_id] = []
                self.parent_children_index[parent_id].append(region)

    def get_region_by_id(self, region_id):
        return self.region_by_id.get(region_id)

    def get_region_by_name(self, name):
        regions = self.alias_index.get(name, [])
        if regions:
            return regions[0]
        return None

    def get_children(self, parent_id):
        return self.parent_children_index.get(parent_id, [])

    def get_parent_chain_ids(self, region):
        chain = region.get("parent_chain", [])
        return [p["id"] for p in chain]

    def resolve_parent_at_level(self, region, target_level):
        chain = region.get("parent_chain", [])
        for p in chain:
            if p["level"] == target_level:
                return self.region_by_id.get(p["id"])
        if region["level"] == target_level:
            return region
        return None
