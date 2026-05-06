import sys
import os


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


def main():
    from region_db import RegionDatabase
    from region_extractor import RegionExtractor
    from gui import App

    db_path = resource_path("region_db.json")
    region_db = RegionDatabase.load(db_path)
    extractor = RegionExtractor.load(region_db)

    app = App(extractor)
    app.run()


if __name__ == "__main__":
    main()
