import sys
import os


def main():
    from region_db import RegionDatabase
    from region_extractor import RegionExtractor
    from gui import App

    db_path = os.path.join(os.path.dirname(__file__), "region_db.json")
    region_db = RegionDatabase.load(db_path)
    extractor = RegionExtractor(region_db)

    app = App(extractor)
    app.run()


if __name__ == "__main__":
    main()
