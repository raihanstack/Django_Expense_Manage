def site_meta(request):
    """Context processor that provides site‑wide SEO metadata.
    The values can be overridden per view by adding a ``site_meta`` key
    to the template context.
    """
    return {
        "site_meta": {
            "site_title": "Amertaka",
            "meta_description": "Track and manage your personal expenses effortlessly with Amertaka.",
            "meta_keywords": "Amertaka, Expense Manager, Budget, Finance, Track Spending, Personal Finance",
            "canonical_url": "https://amertaka.vercel.app/",
            "og_image": "",  # optional – can be set per view if desired
        }
    }
