"""Capital One public product catalog, platforms, and generic team routing seed definitions."""

from typing import List, Dict, Any

CAPITAL_ONE_PRODUCTS: List[Dict[str, Any]] = [
    # Credit Cards
    {
        "id": "venture_x",
        "name": "Venture X Rewards",
        "family": "Credit Cards",
        "description": "Premium travel rewards card with airport lounge access and 10x travel miles.",
    },
    {
        "id": "venture",
        "name": "Venture Rewards",
        "family": "Credit Cards",
        "description": "Unlimited 2x miles travel card with transfer partner flexibility.",
    },
    {
        "id": "savor_one",
        "name": "SavorOne Cash Rewards",
        "family": "Credit Cards",
        "description": "Dining, entertainment, and grocery cash back card with no annual fee.",
    },
    {
        "id": "quicksilver",
        "name": "Quicksilver Cash Rewards",
        "family": "Credit Cards",
        "description": "Flat 1.5% cash back on all purchases card.",
    },
    {
        "id": "platinum",
        "name": "Capital One Platinum",
        "family": "Credit Cards",
        "description": "Credit building and credit reconstruction card with automatic credit line reviews.",
    },
    {
        "id": "spark_cash_plus",
        "name": "Spark Cash Plus",
        "family": "Credit Cards",
        "description": "Small business charge card with unlimited 2% cash back.",
    },

    # Consumer Banking (360)
    {
        "id": "banking_360_checking",
        "name": "360 Checking",
        "family": "Consumer Banking",
        "description": "Fee-free checking account with debit card, mobile check deposit, and early paycheck.",
    },
    {
        "id": "banking_360_savings",
        "name": "360 Performance Savings",
        "family": "Consumer Banking",
        "description": "High-yield online savings account with fee-free transfers.",
    },
    {
        "id": "banking_360_cd",
        "name": "360 Certificate of Deposit",
        "family": "Consumer Banking",
        "description": "Fixed-rate savings certificates with guaranteed APY terms.",
    },

    # Auto Financing
    {
        "id": "auto_navigator",
        "name": "Auto Navigator",
        "family": "Auto Financing",
        "description": "Online auto financing pre-qualification tool without affecting credit score.",
    },
    {
        "id": "auto_refinance",
        "name": "Auto Refinancing",
        "family": "Auto Financing",
        "description": "Vehicle loan refinancing to lower monthly payments or interest rates.",
    },

    # Digital & Software Platforms
    {
        "id": "c1_mobile_ios",
        "name": "Capital One Mobile (iOS)",
        "family": "Digital & Software Platforms",
        "description": "iOS mobile banking app supporting Face ID, instant card lock, and mobile deposit.",
    },
    {
        "id": "c1_mobile_android",
        "name": "Capital One Mobile (Android)",
        "family": "Digital & Software Platforms",
        "description": "Android mobile banking application supporting biometrics and account management.",
    },
    {
        "id": "eno_virtual_assistant",
        "name": "Eno Digital Assistant",
        "family": "Digital & Software Platforms",
        "description": "AI virtual assistant providing virtual card numbers, fraud alerts, and text banking.",
    },
    {
        "id": "c1_shopping_extension",
        "name": "Capital One Shopping",
        "family": "Digital & Software Platforms",
        "description": "Browser extension and app providing automated coupon codes and cash back shopping.",
    },
    {
        "id": "creditwise",
        "name": "CreditWise",
        "family": "Digital & Software Platforms",
        "description": "Free credit score tracking, dark web scan, and identity alert tool.",
    },

    # Physical & Hybrid Spaces
    {
        "id": "c1_cafe",
        "name": "Capital One Cafés",
        "family": "Physical & Hybrid Spaces",
        "description": "Co-working spaces offering handcrafted Peet's Coffee discounts, Wi-Fi, and ambassadors.",
    },
    {
        "id": "c1_branch_network",
        "name": "Capital One Bank Branches",
        "family": "Physical & Hybrid Spaces",
        "description": "Traditional brick-and-mortar retail bank branches and teller desks.",
    },
    {
        "id": "c1_atm_network",
        "name": "Capital One & Allpoint ATMs",
        "family": "Physical & Hybrid Spaces",
        "description": "Fee-free network of over 70,000 ATMs across the United States.",
    },
]

INGESTION_SOURCES: List[Dict[str, Any]] = [
    {
        "id": "apple_app_store",
        "name": "Apple App Store",
        "platform_type": "mobile_store",
        "description": "Public iOS customer reviews and ratings.",
    },
    {
        "id": "google_play_store",
        "name": "Google Play Store",
        "platform_type": "mobile_store",
        "description": "Public Android customer reviews and ratings.",
    },
    {
        "id": "chrome_web_store",
        "name": "Chrome Web Store",
        "platform_type": "browser_extension",
        "description": "Browser extension store reviews for Capital One Shopping.",
    },
    {
        "id": "google_places",
        "name": "Google Maps & Places",
        "platform_type": "physical_location",
        "description": "Location-specific reviews for Capital One Cafés and bank branches.",
    },
    {
        "id": "trustpilot",
        "name": "Trustpilot Reviews",
        "platform_type": "web_review",
        "description": "Independent public consumer ratings and feedback site.",
    },
    {
        "id": "synthetic_stream",
        "name": "Synthetic Multi-Platform Generator",
        "platform_type": "synthetic_stream",
        "description": "Calibrated synthetic feedback generator replicating real platform distributions.",
    },
]

BUSINESS_TEAMS: List[Dict[str, Any]] = [
    {
        "id": "digital_engineering_mobile",
        "name": "Digital Engineering - Mobile Platform",
        "lead_email": "mobile-engineering@acme.internal",
        "slack_channel": "#team-mobile-eng",
        "routing_patterns": ["authentication", "session_expiration", "biometric_login", "app_crash", "mobile_deposit"],
    },
    {
        "id": "payments_operations",
        "name": "Payments & Card Operations",
        "lead_email": "payments-ops@acme.internal",
        "slack_channel": "#team-payments-ops",
        "routing_patterns": ["transaction_failure", "card_declined", "charge_dispute", "wire_delay", "foreign_fee"],
    },
    {
        "id": "travel_lounges_product",
        "name": "Travel & Airport Lounges Product",
        "lead_email": "travel-product@acme.internal",
        "slack_channel": "#team-travel-lounges",
        "routing_patterns": ["lounge_access", "lounge_crowding", "travel_portal", "mile_transfer", "partner_booking"],
    },
    {
        "id": "cafe_operations",
        "name": "Café & Branch Operations",
        "lead_email": "cafe-ops@acme.internal",
        "slack_channel": "#team-cafe-ops",
        "routing_patterns": ["cafe_experience", "wifi_outage", "beverage_discount", "ambassador_service", "atm_maintenance"],
    },
    {
        "id": "digital_ai_security",
        "name": "Digital AI & Security (Eno)",
        "lead_email": "eno-ai@acme.internal",
        "slack_channel": "#team-eno-security",
        "routing_patterns": ["virtual_cards", "merchant_rejection", "fraud_alert_false_positive", "assistant_accuracy"],
    },
    {
        "id": "shopping_engineering",
        "name": "Shopping Platform Engineering",
        "lead_email": "shopping-eng@acme.internal",
        "slack_channel": "#team-shopping-platform",
        "routing_patterns": ["browser_extension", "cashback_tracking", "coupon_code_failure", "extension_freeze"],
    },
    {
        "id": "customer_experience",
        "name": "Customer Experience & Escalations",
        "lead_email": "cx-leadership@acme.internal",
        "slack_channel": "#team-cx-escalations",
        "routing_patterns": ["phone_hold_time", "agent_unhelpful", "account_closure", "credit_limit_decrease"],
    },
]
