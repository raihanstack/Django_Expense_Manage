def site_meta(request):
    """Context processor that provides site‑wide SEO metadata.
    The values can be overridden per view by adding a ``site_meta`` key
    to the template context.
    """
    return {
        "site_meta": {
            "site_title": "TakaSave",
            "meta_description": "Track and manage your personal expenses effortlessly with TakaSave.",
            "meta_keywords": "TakaSave, Expense Manager, Budget, Finance, Track Spending, Personal Finance",
            "canonical_url": "https://takasave.vercel.app/",
            "og_image": "",  # optional – can be set per view if desired
        }
    }
