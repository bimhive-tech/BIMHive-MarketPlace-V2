"""Seeds the Terms of Service and Privacy Policy as legal articles.

Written generically: no company legal name, jurisdiction or contact email yet.
Have them reviewed and completed before relying on them. Editable in /admin
(Knowledge Base & Legal Pages → Articles). Re-running replaces the sections of
these two articles only.
"""
from django.db import migrations

CONTACT = (
    "If you have a question about this page, open a ticket from Support Tickets in your BIMHIVE "
    "account and our team will reply there."
)

TERMS_SECTIONS = [
    (
        "About these terms",
        "These Terms of Service apply whenever you use the BIMHIVE website, create an account, buy or "
        "download a product, or activate a BIMHIVE plugin. By doing any of those things you agree to "
        "these terms. If you don't agree, please don't use the site.\n\n"
        "BIMHIVE is a marketplace for Revit plugins, scripts, templates and other digital tools for the "
        "architecture, engineering and construction industry. Some products are made by BIMHIVE and "
        "others by independent sellers (\"partners\").",
    ),
    (
        "Your account",
        "You need an account to buy, claim or download products. Please give accurate information and "
        "keep your password to yourself; you're responsible for what happens under your account.\n\n"
        "You can see the devices signed in to your account and sign them out from your account settings, "
        "and you can delete your account at any time. Deleting your account ends access to the licenses "
        "attached to it.",
    ),
    (
        "Licenses, not ownership",
        "When you buy, claim or subscribe to a product, you receive a license to use it. You don't buy "
        "the software itself. Unless a product page says otherwise, a license is personal to your "
        "account and may be used on the number of computers (seats) stated for that purchase or plan.\n\n"
        "Plugins check their license with BIMHIVE when they start. To do that, a plugin sends its product "
        "code, your license key and a hashed identifier of the computer it runs on. A plugin that can't "
        "confirm a valid license may stop working until it can.",
    ),
    (
        "Free products, trials and memberships",
        "Free products are licensed the same way as paid ones and remain subject to these terms. We may "
        "stop offering a free product, or change it to a paid product, at any time.\n\n"
        "Trials run for the period shown when you start them and end automatically.\n\n"
        "A membership plan gives access to the products its tier covers for as long as the membership is "
        "active. When it ends, licenses that came from the membership stop working. Products you bought "
        "separately are not affected.",
    ),
    (
        "Prices and payments",
        "Prices are shown on each product and plan page. Payments are processed by a third-party payment "
        "provider; BIMHIVE doesn't receive or store your full card details.\n\n"
        "An order is complete once the payment provider confirms payment. If a payment is reversed or "
        "disputed, the licenses from that order can be deactivated.\n\n"
        "If you believe you were charged in error or a product doesn't work as described, contact us "
        "through Support Tickets and we will look into it.",
    ),
    (
        "Products from partners",
        "Partners are responsible for the products they list, including their descriptions, updates and "
        "support. We review each product before it is listed, but that review is not a guarantee that a "
        "product is free of errors or suitable for your project.",
    ),
    (
        "Acceptable use",
        "You agree not to:\n"
        "- share, sell or publish license keys, or use one license on more computers than it allows;\n"
        "- remove, bypass or tamper with a product's licensing or activation;\n"
        "- copy, resell or redistribute products, except where a product's own license allows it;\n"
        "- reverse engineer products, except where the law allows it despite this restriction;\n"
        "- use the site to break the law, upload malicious code, or disrupt the service for others.",
    ),
    (
        "Revoking licenses",
        "We may deactivate a license, or suspend or close an account, if we reasonably believe these "
        "terms have been broken, a payment was fraudulent or reversed, or a license is being misused. "
        "This applies to free and paid products alike.",
    ),
    (
        "Reviews and other content you submit",
        "When you post a review, open a support ticket, or submit a product as a partner, you confirm "
        "that you have the right to share that content, and you allow BIMHIVE to store and display it as "
        "needed to run the marketplace. We may remove content that is unlawful, abusive or misleading.",
    ),
    (
        "Intellectual property",
        "The BIMHIVE name, logo and website belong to BIMHIVE. Each product belongs to BIMHIVE or to the "
        "partner who made it.\n\n"
        "Autodesk and Revit are registered trademarks of Autodesk, Inc. BIMHIVE is not affiliated with or "
        "endorsed by Autodesk.",
    ),
    (
        "No warranty",
        "Products and the website are provided \"as is\" and \"as available\". To the extent the law "
        "allows, we don't promise that they will be error-free, uninterrupted, or suitable for a "
        "particular purpose.\n\n"
        "Automation tools change your models. Always keep backups, and check results before relying on "
        "them for real projects.",
    ),
    (
        "Limitation of liability",
        "To the extent the law allows, BIMHIVE is not liable for indirect or consequential losses, such "
        "as lost profits, lost data, or project delays, arising from your use of the website or any "
        "product. Nothing in these terms limits liability that cannot be limited by law.",
    ),
    (
        "Changes to these terms",
        "We may update these terms as the marketplace changes. The date at the top of this page shows "
        "when they were last updated. If you keep using BIMHIVE after an update, the updated terms apply.",
    ),
    ("Contact", CONTACT),
]

PRIVACY_SECTIONS = [
    (
        "About this policy",
        "This Privacy Policy explains what information BIMHIVE collects when you use the website and our "
        "plugins, why we collect it, and the choices you have.",
    ),
    (
        "Information you give us",
        "- Account details: your name, email address and password. Passwords are stored only in hashed "
        "form, never as plain text.\n"
        "- Profile details you choose to add, such as profession, country, company or university.\n"
        "- Billing details needed for orders, such as your billing address.\n"
        "- Support tickets, reviews and anything else you write on the site.\n"
        "- If you apply to sell, your company name, logo, description and website.",
    ),
    (
        "Information from your purchases and licenses",
        "We keep a record of your orders, licenses, trials and memberships so you can download and "
        "activate what you're entitled to.\n\n"
        "Payments are handled by a third-party payment provider. We receive whether a payment succeeded "
        "and the order details, not your full card number.",
    ),
    (
        "Information from our plugins",
        "When a BIMHIVE plugin starts, it contacts BIMHIVE to check its license. It sends the product "
        "code, your license key and a hashed identifier of the computer. We use this only to check that "
        "the license is valid and to enforce the number of computers it may be used on. We record when "
        "each computer was first and last seen.",
    ),
    (
        "Information collected automatically",
        "Like most websites, our servers may log technical information such as your IP address, browser "
        "type and the pages requested. We use it to keep the service secure and to fix problems.\n\n"
        "We don't use advertising or analytics trackers.",
    ),
    (
        "Cookies and browser storage",
        "We use a small number of cookies that the site needs to work: one keeps you signed in, and one "
        "protects forms against cross-site request forgery.\n\n"
        "Your cart is saved in your browser's local storage so it survives a page reload, and if you "
        "close the promotion bar, that choice is remembered for the rest of your browser session. "
        "Neither is sent to anyone else.",
    ),
    (
        "How we use your information",
        "- To run your account and deliver the products you buy, claim or subscribe to.\n"
        "- To check licenses and prevent misuse.\n"
        "- To answer support tickets and notify you about your orders, reviews or seller application.\n"
        "- To keep the service secure and working.\n"
        "- To meet legal and accounting obligations.",
    ),
    (
        "Who we share it with",
        "We don't sell your personal information. We share it only with:\n"
        "- the payment provider that processes your payments;\n"
        "- the hosting and file storage providers that run the site on our behalf;\n"
        "- authorities, where the law requires it.\n\n"
        "Partners who sell on BIMHIVE can see order information for their own products, such as the "
        "product, amount and date, but not your name or contact details.",
    ),
    (
        "How long we keep it",
        "We keep your account information while your account exists. Order and payment records may be "
        "kept longer where accounting or legal rules require it.",
    ),
    (
        "Security",
        "We protect your information with measures such as encrypted connections (HTTPS), hashed "
        "passwords and access controls for staff. No online service can be perfectly secure, so please "
        "use a strong, unique password.",
    ),
    (
        "Your choices",
        "- You can view and update your profile details from your account.\n"
        "- You can see your signed-in devices and sign any of them out.\n"
        "- You can delete your account from your account settings.\n"
        "- You can ask us for a copy of your information, or ask us to correct or delete it, through "
        "Support Tickets.",
    ),
    (
        "Children",
        "BIMHIVE is a professional service and isn't directed at children. We don't knowingly collect "
        "information from children.",
    ),
    (
        "Changes to this policy",
        "We may update this policy as the service changes. The date at the top of this page shows when "
        "it was last updated.",
    ),
    ("Contact", CONTACT),
]

PAGES = [
    (
        "terms-of-service",
        "Terms of Service",
        "The rules for using BIMHIVE, buying or claiming products, and using their licenses.",
        TERMS_SECTIONS,
    ),
    (
        "privacy-policy",
        "Privacy Policy",
        "What information BIMHIVE collects, why, and the choices you have.",
        PRIVACY_SECTIONS,
    ),
]


def seed_legal_pages(apps, schema_editor):
    Article = apps.get_model("knowledge", "Article")
    ArticleSection = apps.get_model("knowledge", "ArticleSection")
    for order, (slug, title, summary, sections) in enumerate(PAGES):
        article, _ = Article.objects.update_or_create(
            slug=slug,
            defaults={"kind": "legal", "title": title, "summary": summary, "is_published": True, "sort_order": order},
        )
        ArticleSection.objects.filter(article=article).delete()
        for position, (section_title, body) in enumerate(sections):
            ArticleSection.objects.create(article=article, sort_order=position, title=section_title, body=body)


def remove_legal_pages(apps, schema_editor):
    apps.get_model("knowledge", "Article").objects.filter(slug__in=[slug for slug, *_ in PAGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0002_revit_automation_guide")]

    operations = [migrations.RunPython(seed_legal_pages, remove_legal_pages)]
