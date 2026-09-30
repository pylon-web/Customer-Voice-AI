"""Synthetic review generator for Capital One public products and platforms.

Generates 10,000+ realistic multi-product customer reviews across 6 weeks with:
- Positive, neutral, and negative distributions
- Emerging issue surges (Venture X Lounge Crowding, iOS Biometrics, Eno Virtual Cards)
- Improving trend signals (Capital One Shopping Extension memory fix)
- Geographic concentration patterns (Austin & Chicago Café Wi-Fi)
- Ground-truth evaluation tags for AI model benchmarking
"""

import json
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from app.models.seeds import CAPITAL_ONE_PRODUCTS, INGESTION_SOURCES

# Fixed random seed for deterministic reproduction when requested
DEFAULT_SEED = 42

LOCATIONS = [
    "New York, NY", "Chicago, IL", "Austin, TX", "Los Angeles, CA",
    "Dallas, TX", "Denver, CO", "San Francisco, CA", "Seattle, WA",
    "Miami, FL", "Boston, MA", "Atlanta, GA", "Washington, DC",
    "Philadelphia, PA", "Phoenix, AZ", "Houston, TX"
]

POSITIVE_TEMPLATES = [
    ("venture_x", "travel_perks", "unbeatable_miles", "Venture X is by far the best travel card! 10x miles on Capital One Travel portal booked my flights to Europe effortlessly.", "Best travel card on the market", 5),
    ("venture_x", "lounge_access", "lounge_quality", "Visited the Capital One lounge at DFW and the food and cocktails were incredible. Worth the annual fee alone.", "Exceptional lounge experience", 5),
    ("savor_one", "rewards", "dining_cashback", "Getting 3% cashback on all my dining, groceries, and entertainment with SavorOne and zero annual fee. Outstanding card!", "My everyday daily driver card", 5),
    ("quicksilver", "rewards", "flat_cashback", "Simple, no-fuss 1.5% cashback on every single purchase. No rotating categories to remember.", "Great straightforward card", 5),
    ("banking_360_checking", "banking_features", "early_paycheck", "My paycheck arrives 2 days early every time with 360 Checking. No hidden fees and great ATM network.", "Best fee-free checking", 5),
    ("banking_360_savings", "interest_rate", "high_yield_rate", "360 Performance Savings has a consistently high APY. Transfers to checking are instant.", "Consistently great savings yield", 5),
    ("auto_navigator", "financing", "smooth_preapproval", "Auto Navigator showed me my real rate with no hit to my credit. Walked into the dealership and drove off in 45 minutes.", "Easiest car buying experience ever", 5),
    ("eno_virtual_assistant", "virtual_cards", "fraud_prevention", "Eno generated a virtual card for a suspicious merchant and blocked an unauthorized recurring charge. Lifesaver!", "Eno virtual cards are brilliant", 5),
    ("c1_shopping_extension", "savings", "coupon_savings", "Capital One Shopping automatically applied a 20% promo code at checkout on Macy's. Saved $45 instantly.", "Saved me real money effortlessly", 5),
    ("c1_cafe", "cafe_ambiance", "great_coworking", "The Capital One Café in Austin is fantastic. 50% off Peet's coffee with my card and great quiet booths to work from.", "Best coffee and co-working spot", 5),
    ("c1_mobile_ios", "ui_ux", "intuitive_app", "Clean, responsive mobile app. Face ID is instant and tracking recent transactions is super clear.", "Top tier banking app", 5),
]

NEUTRAL_TEMPLATES = [
    ("venture_x", "customer_service", "average_support", "Card perks are decent, but phone support took about 15 minutes on hold to answer a statement question.", "Average support experience", 3),
    ("savor_one", "ui_ux", "app_navigation", "Good rewards, but the mobile app sometimes takes a while to reflect pending merchant authorizations.", "Solid card, app could be faster", 3),
    ("auto_navigator", "dealership", "dealer_coordination", "Auto Navigator gave a good rate estimate, but the dealership finance manager took an hour to find it in their system.", "Good tool, slow dealer", 3),
    ("banking_360_checking", "atm_access", "atm_availability", "Account is fine, but wish there were more physical Capital One deposit ATMs in my suburban area.", "Good digital bank, fewer local ATMs", 3),
    ("c1_cafe", "cafe_ambiance", "busy_seating", "Love the half-price coffee with Capital One cards, but finding an open table on weekday afternoons is tough.", "Nice perks but often crowded", 3),
    ("creditwise", "credit_score", "score_update", "Good free score monitoring tool, but score updates only once a week compared to daily trackers.", "Helpful basic credit check", 3),
]

# Baseline negative templates (normal recurring operational friction)
BASELINE_NEGATIVE_TEMPLATES = [
    ("banking_360_checking", "mobile_deposit", "camera_detection_failure", "Mobile check deposit keeps saying check image is blurry even in direct sunlight.", "Mobile deposit camera bug", 1, "high", "deposit_check"),
    ("savor_one", "fees_and_charges", "foreign_fee_misunderstanding", "Thought foreign transactions were fee-free, but saw a conversion surcharge on my European trip statement.", "Unexpected transaction surcharge", 2, "medium", "dispute_fee"),
    ("auto_refinance", "customer_service", "document_request_delay", "Submitted my vehicle title documents two weeks ago and still haven't heard back from loan underwriting.", "Slow loan processing time", 2, "medium", "refinance_auto"),
    ("platinum", "credit_limit", "credit_limit_stagnant", "Have paid on time for 9 months straight and automatic credit line increase review has not happened.", "No credit limit increase", 2, "low", "increase_credit_line"),
    ("banking_360_savings", "transfers", "external_transfer_hold", "External bank transfer to my 360 savings took 4 business days to clear. Too slow for emergency funds.", "Slow ACH transfer clearance", 2, "medium", "transfer_funds"),
    ("c1_mobile_android", "authentication", "fingerprint_sensor_glitch", "Android app frequently fails fingerprint biometric prompt, forcing manual password typing.", "Fingerprint login unreliable", 2, "medium", "login"),
]

# Emerging Spikes & Trends Templates
SPIKE_VENTURE_X_LOUNGE = [
    ("venture_x", "lounge_access", "lounge_crowding_denial", "Arrived at DFW lounge with my Venture X card and was turned away due to over 90-minute waitlist.", "Turned away at DFW lounge", 1, "critical", "lounge_entry"),
    ("venture_x", "lounge_access", "lounge_crowding_denial", "DFW Capital One Lounge had a line wrapping around the terminal. Could not enter before flight.", "Lounge wait time unacceptable", 1, "critical", "lounge_entry"),
    ("venture_x", "lounge_access", "lounge_crowding_denial", "Pay $395 annual fee specifically for airport lounge access, but Dallas lounge capacity is full every Friday.", "Cannot use key card perk", 1, "high", "lounge_entry"),
    ("venture_x", "lounge_access", "lounge_crowding_denial", "Denver lounge was completely packed and staff told us entry was restricted to boarding in 1 hour.", "Lounge capacity limits too strict", 1, "high", "lounge_entry"),
]

SPIKE_IOS_BIOMETRIC = [
    ("c1_mobile_ios", "authentication", "biometric_login_failure", "Latest app update v6.14 completely broke Face ID on iPhone 15. App crashes to home screen.", "App crashes on Face ID", 1, "critical", "login"),
    ("c1_mobile_ios", "authentication", "biometric_login_failure", "Cannot log into Capital One app on iOS after recent update. Face ID prompt freezes immediately.", "Face ID freeze on iOS v6.14", 1, "critical", "login"),
    ("c1_mobile_ios", "authentication", "biometric_login_failure", "Mobile app immediately quits when attempting biometric authentication on iOS. Urgent bug fix needed.", "Instant crash on biometrics", 1, "critical", "login"),
    ("c1_mobile_ios", "authentication", "biometric_login_failure", "iOS app closes unexpectedly on face recognition prompt every single time.", "Unable to access account on iPhone", 1, "critical", "login"),
]

SPIKE_ENO_VIRTUAL_CARDS = [
    ("eno_virtual_assistant", "virtual_cards", "merchant_rejection", "Eno generated a virtual card for BestBuy.com and it was declined as an unsupported card type.", "Eno virtual card declined by merchant", 1, "high", "online_checkout"),
    ("eno_virtual_assistant", "virtual_cards", "merchant_rejection", "Online retailer rejected my Eno virtual card number claiming it is an invalid prepaid card.", "Virtual card rejected as prepaid", 2, "high", "online_checkout"),
    ("eno_virtual_assistant", "virtual_cards", "merchant_rejection", "Target online checkout keeps throwing payment error with Eno virtual card.", "Eno card failing at online checkout", 1, "high", "online_checkout"),
]

IMPROVING_SHOPPING_EXTENSION = [
    ("c1_shopping_extension", "browser_extension", "extension_freeze", "Capital One Shopping extension uses 100% CPU and causes Chrome browser tabs to freeze.", "Extension freezes browser tabs", 1, "high", "browse_deals"),
    ("c1_shopping_extension", "browser_extension", "extension_freeze", "Severe memory leak in Capital One Shopping Chrome extension on checkout pages.", "Chrome tab crash due to extension", 1, "high", "browse_deals"),
]

GEO_CAFE_WIFI = [
    ("c1_cafe", "cafe_experience", "wifi_outage", "Wi-Fi in this Capital One Café disconnects every 5 minutes. Impossible to get remote work done.", "Café Wi-Fi unworkable", 1, "medium", "cafe_work"),
    ("c1_cafe", "cafe_experience", "wifi_outage", "Internet at the Café is down again. Baristas are great but the network router has no internet connection.", "Internet down at café location", 1, "medium", "cafe_work"),
]


class SyntheticReviewGenerator:
    """Configurable synthetic data generator producing realistic multi-product review streams."""

    def __init__(self, seed: Optional[int] = DEFAULT_SEED):
        if seed is not None:
            random.seed(seed)
        self.products = CAPITAL_ONE_PRODUCTS
        self.sources = INGESTION_SOURCES

    def _get_platform_for_product(self, product_id: str) -> str:
        """Select realistic review platforms based on the product type."""
        if product_id == "c1_mobile_ios":
            return "apple_app_store"
        if product_id == "c1_mobile_android":
            return "google_play_store"
        if product_id == "c1_shopping_extension":
            return random.choice(["chrome_web_store", "apple_app_store"])
        if product_id in {"c1_cafe", "c1_branch_network", "c1_atm_network"}:
            return random.choice(["google_places", "trustpilot"])
        return random.choice(["apple_app_store", "google_play_store", "trustpilot"])

    def generate_review(
        self,
        created_at: datetime,
        force_category: Optional[str] = None,
        force_product: Optional[str] = None,
        force_template: Optional[tuple] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single structured review with ground-truth analysis labels."""
        review_id = f"c1-rev-{uuid.uuid4().hex[:10]}"
        selected_location = location or random.choice(LOCATIONS)

        if force_template:
            prod_id, cat, issue, text, title, rating, severity, intent = force_template
            sentiment = "positive" if rating >= 4 else ("neutral" if rating == 3 else "negative")
            score = 0.85 if rating >= 4 else (0.0 if rating == 3 else -0.85)
            confidence = round(random.uniform(0.90, 0.99), 2)
        else:
            # Baseline selection: ~50% positive, 18% neutral, 32% negative
            sentiment_roll = random.random()
            if sentiment_roll < 0.50:
                prod_id, cat, issue, text, title, rating = random.choice(POSITIVE_TEMPLATES)
                sentiment = "positive"
                score = round(random.uniform(0.65, 0.98), 2)
                severity = "low"
                intent = "general_praise"
                confidence = round(random.uniform(0.88, 0.98), 2)
            elif sentiment_roll < 0.68:
                prod_id, cat, issue, text, title, rating = random.choice(NEUTRAL_TEMPLATES)
                sentiment = "neutral"
                score = round(random.uniform(-0.15, 0.15), 2)
                severity = "low"
                intent = "general_feedback"
                confidence = round(random.uniform(0.80, 0.92), 2)
            else:
                prod_id, cat, issue, text, title, rating, severity, intent = random.choice(BASELINE_NEGATIVE_TEMPLATES)
                sentiment = "negative"
                score = round(random.uniform(-0.95, -0.60), 2)
                confidence = round(random.uniform(0.85, 0.97), 2)

        if force_product:
            prod_id = force_product

        source_id = self._get_platform_for_product(prod_id)

        prefixes = ["", "Honest review: ", "Update: ", "Customer feedback: ", "FYI: "]
        text = f"{random.choice(prefixes)}{text}"

        return {
            "id": review_id,
            "source_id": source_id,
            "product_id": prod_id,
            "location": selected_location,
            "rating": rating,
            "review_title": title,
            "review_text": text,
            "created_at": created_at.isoformat(),
            "metadata_json": {
                "synthetic": True,
                "device": random.choice(["iPhone 15 Pro", "iPhone 14", "Samsung Galaxy S24", "Google Pixel 8", "Desktop Chrome"]),
                "app_version": "v6.14.0" if "ios" in prod_id else "v5.8.2",
            },
            "_ground_truth": {
                "sentiment": sentiment,
                "sentiment_score": score,
                "category": cat,
                "issue": issue,
                "severity": severity,
                "customer_intent": intent,
                "confidence": confidence,
            }
        }

    def generate_dataset(self, total_count: int = 10000, weeks: int = 6) -> List[Dict[str, Any]]:
        """Generate a complete dataset of exact size total_count distributed across weeks."""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(weeks=weeks)
        reviews: List[Dict[str, Any]] = []

        scale = max(0.1, total_count / 10000.0)
        base_per_week = total_count // weeks

        for week_idx in range(weeks):
            week_start = start_date + timedelta(weeks=week_idx)

            # Injected counts scaled proportionally to dataset size
            if week_idx < 3:
                lounge_count = int(round(6 * scale))
                ios_count = int(round(8 * scale))
                eno_count = int(round(6 * scale))
                shopping_count = int(round(50 * scale))
            elif week_idx == 3:
                lounge_count = int(round(15 * scale))
                ios_count = int(round(12 * scale))
                eno_count = int(round(15 * scale))
                shopping_count = int(round(25 * scale))
            elif week_idx == 4:
                lounge_count = int(round(55 * scale))
                ios_count = int(round(65 * scale))
                eno_count = int(round(35 * scale))
                shopping_count = int(round(10 * scale))
            else:
                lounge_count = int(round(110 * scale))
                ios_count = int(round(130 * scale))
                eno_count = int(round(70 * scale))
                shopping_count = int(round(3 * scale))

            cafe_wifi_count = int(round(15 * scale))

            # Generate trend spikes
            for _ in range(lounge_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                tmpl = random.choice(SPIKE_VENTURE_X_LOUNGE)
                reviews.append(self.generate_review(ts, force_template=tmpl, location=random.choice(["Dallas, TX", "Denver, CO"])))

            for _ in range(ios_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                tmpl = random.choice(SPIKE_IOS_BIOMETRIC)
                reviews.append(self.generate_review(ts, force_template=tmpl))

            for _ in range(eno_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                tmpl = random.choice(SPIKE_ENO_VIRTUAL_CARDS)
                reviews.append(self.generate_review(ts, force_template=tmpl))

            for _ in range(shopping_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                tmpl = random.choice(IMPROVING_SHOPPING_EXTENSION)
                reviews.append(self.generate_review(ts, force_template=tmpl))

            for _ in range(cafe_wifi_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                tmpl = random.choice(GEO_CAFE_WIFI)
                loc = random.choice(["Austin, TX", "Chicago, IL"])
                reviews.append(self.generate_review(ts, force_template=tmpl, location=loc))

            already_generated = lounge_count + ios_count + eno_count + shopping_count + cafe_wifi_count
            regular_count = max(0, base_per_week - already_generated)

            for _ in range(regular_count):
                ts = week_start + timedelta(seconds=random.randint(0, int(7 * 86400)))
                reviews.append(self.generate_review(ts))

        # Adjust length strictly to total_count
        if len(reviews) > total_count:
            reviews = reviews[:total_count]
        while len(reviews) < total_count:
            ts = start_date + timedelta(seconds=random.randint(0, int(weeks * 7 * 86400)))
            reviews.append(self.generate_review(ts))

        reviews.sort(key=lambda r: r["created_at"])
        return reviews

    def save_json(self, reviews: List[Dict[str, Any]], filepath: str) -> None:
        """Save reviews to a formatted JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2)

    def save_csv(self, reviews: List[Dict[str, Any]], filepath: str) -> None:
        """Save reviews to a CSV file."""
        if not reviews:
            return
        fieldnames = [
            "id", "source_id", "product_id", "location", "rating",
            "review_title", "review_text", "created_at",
            "ground_truth_sentiment", "ground_truth_category", "ground_truth_issue",
            "ground_truth_severity", "ground_truth_confidence"
        ]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reviews:
                gt = r.get("_ground_truth", {})
                writer.writerow({
                    "id": r["id"],
                    "source_id": r["source_id"],
                    "product_id": r["product_id"],
                    "location": r.get("location", ""),
                    "rating": r["rating"],
                    "review_title": r.get("review_title", ""),
                    "review_text": r["review_text"],
                    "created_at": r["created_at"],
                    "ground_truth_sentiment": gt.get("sentiment", ""),
                    "ground_truth_category": gt.get("category", ""),
                    "ground_truth_issue": gt.get("issue", ""),
                    "ground_truth_severity": gt.get("severity", ""),
                    "ground_truth_confidence": gt.get("confidence", 0.0),
                })
