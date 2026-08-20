# test_mutable.py

from backend.app.services.semantic_review_service import (
    review_code_semantically,
)

code = """
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("apple"))
print(add_item("banana"))
print(add_item("orange"))
"""

print(review_code_semantically(code))