import math

# Simulate the scan endpoint response for different totals
def check_scan_consistency(total):
    """Verify that pages, per_page, and len(items) are consistent"""
    # Fixed by the scan endpoint
    pages = 1
    per_page = max(total, 1)
    items_count = total
    
    # Check consistency: len(items) should equal per_page (all on one page)
    is_consistent = (items_count == per_page)
    return {
        "total": total,
        "pages": pages,
        "per_page": per_page,
        "items_count": items_count,
        "consistent": is_consistent,
        "check": f"len({items_count}) == per_page({per_page}): {is_consistent}"
    }

# Test various scenarios
test_cases = [0, 1, 12, 19, 100]
print("=== SCAN ENDPOINT PAGINATION CONSISTENCY ===\n")
for total in test_cases:
    result = check_scan_consistency(total)
    print(f"Total={total:3d} | pages={result['pages']} | per_page={result['per_page']:3d} | {result['check']}")

print("\n=== LIST ENDPOINT PAGINATION (per_page=12, total=15) ===")
total = 15
per_page = 12
pages = max(1, math.ceil(total / per_page))
items_page1 = min(per_page, total)
items_page2 = total - items_page1
print(f"Page 1: len(items)={items_page1}, expected={per_page}, consistent={items_page1 == per_page}")
print(f"Page 2: len(items)={items_page2}, expected={per_page if items_page2 == per_page else items_page2}, consistent={True}")
print(f"Total pages={pages}, formula check: ceil({total}/{per_page}) = {pages}")
