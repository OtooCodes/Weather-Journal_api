def replace_mongo_id(doc):
    """Convert Mongo _id to string id for JSON response."""
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc
