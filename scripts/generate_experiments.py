"""
generate_experiments.py
Synthetic A/B experiment dataset generator for the Experimentation Intelligence Agent.

Generates a realistic corpus of e-commerce A/B test records modeled on
enterprise experimentation team conventions:
- 5-digit numeric Test IDs
- Recipe A = Control; treatment variants = Recipe B / C / D
- 10% confidence level (p < 0.10) for significance
- Success metrics as the primary KPI vocabulary
- Three-level analytics granularity: Visitors > Visits > Hits
- Desktop and Mobile analysis splits
- Final recommendation: "Retain Control" or "Adopt Recipe <X>"

Design philosophy:
- Structure & terminology come from realistic templates
- Variation comes from parameterized randomization, NOT an LLM
- ~200 experiments, each a structured JSON record
- Outputs: data/experiments.json + data/experiments_metadata.json
"""

import json
import random
import math
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ─────────────────────────────────────────────
# DOMAIN TAXONOMY
# ─────────────────────────────────────────────

PRODUCT_LINES = ["Discover", "Explore", "Cart & Checkout", "Premiere"]

PAGES = [
    "Home Page",
    "SNP Category Page",
    "Product Stack",
    "PDP",
    "SSB Page",
    "Candy Aisle",
    "Cart",
    "Shipping & Payment",
    "Review",
    "Confirmation",
]

PRODUCT_LINE_PAGES = {
    "Discover": ["Home Page", "SNP Category Page", "Product Stack", "PDP"],
    "Explore":  ["SNP Category Page", "Product Stack", "PDP", "SSB Page"],
    "Cart & Checkout": ["Cart", "Shipping & Payment", "Review", "Confirmation", "Candy Aisle"],
    "Premiere": ["Home Page", "SNP Category Page", "PDP"],
}

FEATURES = [
    "Masthead", "Search", "Banner", "Nav Bar (ANAV)", "Category Strip",
    "Product Stack Tile", "PDP Configurator", "Add-to-Cart CTA",
    "Cart Summary", "Checkout Progress Bar", "Warranty Selector",
    "Recommendations Carousel", "Shipping Estimator", "Promo Banner",
    "Trust Badges", "Comparison Tool",
]

SUCCESS_METRICS = [
    "Conversion Rate", "RPV", "AOV", "RPU", "Engagement",
    "Scroll Rate", "Click-Through Rate", "Time Spent on Site",
    "Forward Movement", "Backward Movement",
    "First Time Visit Rate", "Return Visit Rate",
]

GUARDRAIL_METRICS = [
    "Bounce Rate", "Exit Rate", "Page Load Time",
    "Error Rate", "Cart Abandonment Rate",
]

NAMES = [
    "Priya", "Rahul", "Anika", "Karan", "Meera", "Arjun", "Divya", "Vikram",
    "Lakshmi", "Aditya", "Sneha", "Rohan", "Kavya", "Siddharth", "Riya",
    "Sarah", "Michael", "Jessica", "David", "Emily", "Daniel", "Ashley",
]

# ─────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────

PROBLEM_STATEMENTS = [
    "Users dropping off at {page} with no clear progression cue to the next step.",
    "{feature} on {page} has flat engagement over the last 3 quarters; current design assumed but not validated.",
    "Mobile traffic on {page} converts at {gap}% lower than desktop; {feature} suspected as a friction point.",
    "Heat-mapping shows users hovering on {feature} but not clicking through; possible affordance issue.",
    "Returning users skip {feature} on {page}; opportunity to surface relevant content earlier in the flow.",
    "{feature} occupies premium real estate on {page} but shows below-baseline engagement vs benchmarks.",
]

HYPOTHESIS_TEMPLATES = [
    "We believe that updating {feature} on {page} with {change} will {direction_verb} {metric} for {segment} because {reason}.",
    "Replacing the existing {feature} on {page} with {change} will lift {metric} by reducing {friction} for {segment}.",
    "Showing {change} via {feature} on {page} will drive {metric} improvement for {segment} without negatively impacting {guardrail}.",
    "Adding {change} to {feature} on {page} during the {segment} flow will improve {metric}.",
]

CHANGES = [
    "a simplified copy layout", "a more prominent CTA", "social proof tiles",
    "a progress indicator", "inline configurator help", "a one-click upsell prompt",
    "personalized product tiles", "a discount strip", "urgency messaging",
    "trust badge cluster", "a sticky add-to-cart bar", "a modal upsell",
    "auto-filled shipping fields", "a top-rated carousel",
    "a reduced number of form fields", "a real-time stock counter",
    "a free shipping threshold indicator", "tabbed spec organization",
    "a chat entry point", "lazy-loaded product imagery",
    "a streamlined warranty selector", "a comparison shortcut",
]

REASONS = [
    "it reduces cognitive load during the decision step",
    "it surfaces relevant information at the point of intent",
    "it removes friction in the purchase path",
    "it builds trust at a high-drop-off point",
    "prior qualitative research showed user confusion here",
    "competitor analysis revealed this as a gap",
    "session recordings showed users struggling with the current module",
    "it aligns with the mental model of the target segment",
    "it removes an unnecessary step from the configurator flow",
]

FRICTIONS = [
    "decision fatigue", "navigation confusion", "trust hesitation",
    "form abandonment", "unclear value proposition", "perceived slowness",
    "unexpected redirects", "missing information at point of decision",
    "spec overload", "checkout interruption",
]

SEGMENTS = [
    "first time visitors", "return visitors", "mobile visitors",
    "desktop visitors", "tablet visitors", "logged-in users",
    "anonymous visitors", "high-intent visitors", "low-intent visitors",
    "small business buyers", "consumer buyers",
]

DIRECTION_VERBS = ["increase", "lift", "drive", "improve"]

STORY_TEMPLATES = [
    "{feature} engagement {direction_a}, {page} exit rate {direction_b}, downstream forward movement to {next_page} {direction_c}.",
    "Scroll rate on {page} {direction_a}, {feature} click-through {direction_b}, {metric} {direction_c} vs Control.",
    "{page} bounce rate {direction_a}, time spent on {feature} {direction_b}, RPV {direction_c}; story holds across {segment} cohort.",
    "Forward movement from {page} to {next_page} {direction_a}; backward movement to {prev_page} {direction_b}; {metric} change {direction_c}.",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def log_normal_sample(mean, sigma=0.6, floor=400, ceiling=800_000):
    raw = int(math.exp(random.gauss(math.log(mean), sigma)))
    return max(floor, min(ceiling, raw))


def realistic_effect_size(outcome):
    if outcome == "Increased":
        return round(random.uniform(0.01, 0.06), 4)
    elif outcome == "Decreased":
        return round(random.uniform(-0.05, -0.01), 4)
    else:
        return round(random.uniform(-0.012, 0.012), 4)


def compute_required_sample(effect_size, baseline=0.05, alpha=0.10, power=0.80):
    """Sample size at the 10% confidence level (z_alpha two-tailed alpha=0.10 = 1.645)."""
    if effect_size == 0:
        return 999_999
    z_alpha = 1.645
    z_beta = 0.842
    p1 = baseline
    p2 = baseline + abs(effect_size)
    p_bar = (p1 + p2) / 2
    n = ((z_alpha + z_beta) ** 2 * 2 * p_bar * (1 - p_bar)) / ((p2 - p1) ** 2)
    return int(n)


def random_date(start_year=2022, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def direction_word():
    return random.choices(
        ["increased", "decreased", "flat"],
        weights=[0.40, 0.25, 0.35],
    )[0]


def people(role, n=None):
    n = n or random.randint(1, 3)
    return [f"{random.choice(NAMES)} ({role})" for _ in range(n)]


def neighboring_pages(page):
    if page in PAGES:
        idx = PAGES.index(page)
        prev_page = PAGES[idx - 1] if idx > 0 else PAGES[0]
        next_page = PAGES[idx + 1] if idx < len(PAGES) - 1 else PAGES[-1]
    else:
        prev_page, next_page = "Home Page", "PDP"
    return prev_page, next_page


# ─────────────────────────────────────────────
# RECIPE BUILDER
# ─────────────────────────────────────────────

def build_recipes(total_visitors, num_recipes, segment_imbalance=False):
    recipe_names = ["Control"] + [f"Recipe {chr(ord('B') + i)}" for i in range(num_recipes)]
    total_groups = len(recipe_names)

    if segment_imbalance:
        splits = [random.uniform(0.20, 0.30)]
        remaining = 1 - splits[0]
        for _ in range(total_groups - 2):
            s = random.uniform(0.1, remaining / 2)
            splits.append(s)
            remaining -= s
        splits.append(remaining)
    else:
        base = 1 / total_groups
        splits = [base + random.uniform(-0.02, 0.02) for _ in range(total_groups - 1)]
        splits.append(1 - sum(splits))

    recipes = []
    for name, split in zip(recipe_names, splits):
        visitors = int(total_visitors * split)
        visits = int(visitors * random.uniform(1.1, 1.6))
        hits = int(visits * random.uniform(4.0, 9.0))
        description = (
            "Existing experience — no change."
            if name == "Control"
            else f"{random.choice(CHANGES).capitalize()} applied to the tested module."
        )
        recipes.append({
            "recipe": name,
            "description": description,
            "traffic_split_pct": round(split * 100, 1),
            "visitors": visitors,
            "visits": visits,
            "hits": hits,
        })
    return recipes


# ─────────────────────────────────────────────
# DEVICE-LEVEL ANALYSIS
# ─────────────────────────────────────────────

def build_device_analysis(device, recipes, success_metrics, outcome, effect_size, page, feature):
    device_share = random.uniform(0.55, 0.70) if device == "Desktop" else random.uniform(0.30, 0.45)

    metric_results = {}
    for metric in success_metrics:
        per_recipe = {}
        for r in recipes:
            if r["recipe"] == "Control":
                if "Rate" in metric or metric == "Engagement":
                    baseline = round(random.uniform(0.02, 0.15), 4)
                elif metric in ("RPV", "AOV"):
                    baseline = round(random.uniform(40, 220), 2)
                elif metric == "RPU":
                    baseline = round(random.uniform(180, 950), 2)
                elif metric == "Time Spent on Site":
                    baseline = round(random.uniform(90, 360), 1)
                else:
                    baseline = round(random.uniform(0.05, 0.30), 4)
                per_recipe[r["recipe"]] = {"value": baseline}
            else:
                control_value = per_recipe["Control"]["value"]
                if r["recipe"] == "Recipe B" and outcome != "Inconclusive":
                    lift = effect_size + random.uniform(-0.005, 0.005)
                else:
                    lift = random.uniform(-0.01, 0.01)
                new_value = round(control_value * (1 + lift), 4 if control_value < 5 else 2)
                if abs(lift) >= 0.012 and outcome != "Inconclusive":
                    p_value = round(random.uniform(0.001, 0.095), 4)
                else:
                    p_value = round(random.uniform(0.11, 0.85), 4)
                direction = "Increased" if lift > 0.005 else ("Decreased" if lift < -0.005 else "Flat")
                per_recipe[r["recipe"]] = {
                    "value": new_value,
                    "lift_vs_control_pct": round(lift * 100, 2),
                    "p_value": p_value,
                    "direction": direction,
                    "significant_at_10pct": p_value < 0.10,
                }
        metric_results[metric] = per_recipe

    prev_page, next_page = neighboring_pages(page)
    story = random.choice(STORY_TEMPLATES).format(
        feature=feature, page=page, next_page=next_page, prev_page=prev_page,
        metric=random.choice(success_metrics), segment=random.choice(SEGMENTS),
        direction_a=direction_word(), direction_b=direction_word(), direction_c=direction_word(),
    )

    funnel = {
        "page_visits": int(sum(r["visits"] for r in recipes) * device_share),
        "exit_rate": round(random.uniform(0.20, 0.55), 4),
        "forward_movement_rate": round(random.uniform(0.30, 0.65), 4),
        "backward_movement_rate": round(random.uniform(0.05, 0.20), 4),
    }

    return {
        "device": device,
        "device_share_of_traffic_pct": round(device_share * 100, 1),
        "funnel": funnel,
        "metric_results": metric_results,
        "story": story,
    }


# ─────────────────────────────────────────────
# CORE GENERATOR
# ─────────────────────────────────────────────

def generate_experiment() -> dict:
    test_id = str(random.randint(30000, 99999))
    product_line = random.choice(PRODUCT_LINES)
    page = random.choice(PRODUCT_LINE_PAGES[product_line])
    feature = random.choice(FEATURES)

    num_recipes = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]

    success_metrics = random.sample(
        SUCCESS_METRICS,
        k=random.choices([1, 2, 3], weights=[0.55, 0.30, 0.15])[0],
    )
    custom_metrics = []
    if random.random() < 0.40:
        custom_metrics = [
            f"Custom: {random.choice(['module engagement', 'feature scroll-into-view rate', 'configurator-completion rate', 'spec-tab clicks'])}"
        ]
    guardrail = random.choice(GUARDRAIL_METRICS)

    outcome = random.choices(
        ["Increased", "Decreased", "Flat", "Inconclusive"],
        weights=[0.42, 0.13, 0.32, 0.13],
    )[0]

    effect_size = realistic_effect_size(outcome if outcome != "Inconclusive" else "Flat")
    baseline_rate = round(random.uniform(0.03, 0.15), 4)

    total_visitors = log_normal_sample(mean=random.choice([3000, 12000, 40000, 120000]))
    required_n = compute_required_sample(effect_size, baseline=baseline_rate, alpha=0.10)

    flaw_type = "none"
    if total_visitors < required_n * 0.6:
        flaw_type = "underpowered"
    else:
        flaw_type = random.choices(
            ["underpowered", "segment_imbalance", "short_duration", "multiple_metrics", "none"],
            weights=[0.06, 0.07, 0.07, 0.05, 0.75],
        )[0]

    recipes = build_recipes(
        total_visitors, num_recipes,
        segment_imbalance=(flaw_type == "segment_imbalance"),
    )

    duration_days = random.randint(7, 35)
    if flaw_type == "short_duration":
        duration_days = random.randint(1, 4)

    assignment_date = random_date()
    sqa_date = assignment_date + timedelta(days=random.randint(3, 10))
    go_live_date = sqa_date + timedelta(days=random.randint(1, 5))
    end_date = go_live_date + timedelta(days=duration_days)
    deepdive_date = end_date + timedelta(days=random.randint(2, 7))
    om_presentation_date = deepdive_date + timedelta(days=random.randint(1, 5))

    actual_power = (
        min(0.99, max(0.05, total_visitors / required_n * 0.80))
        if required_n < 999_999 else 0.80
    )

    if outcome in ["Increased", "Decreased"]:
        headline_p = round(random.uniform(0.001, 0.095), 4)
    elif outcome == "Flat":
        headline_p = round(random.uniform(0.12, 0.80), 4)
    else:
        headline_p = round(random.uniform(0.08, 0.18), 4)

    hypothesis = random.choice(HYPOTHESIS_TEMPLATES).format(
        feature=feature, page=page, change=random.choice(CHANGES),
        direction_verb=random.choice(DIRECTION_VERBS),
        metric=random.choice(success_metrics), segment=random.choice(SEGMENTS),
        reason=random.choice(REASONS), friction=random.choice(FRICTIONS),
        guardrail=guardrail,
    )
    problem_statement = random.choice(PROBLEM_STATEMENTS).format(
        feature=feature, page=page, gap=random.randint(8, 22),
    )

    critical_questions = random.sample([
        f"Does the change improve {random.choice(success_metrics)} for {random.choice(SEGMENTS)}?",
        f"Does the change negatively impact {guardrail}?",
        "Is the lift consistent across desktop and mobile?",
        f"Does the change affect downstream forward movement to {neighboring_pages(page)[1]}?",
        "Is there a differential effect on first time vs return visitors?",
    ], k=random.randint(2, 3))

    has_desktop = random.random() < 0.95
    has_mobile = random.random() < 0.85
    analysis = {}
    if has_desktop:
        analysis["desktop"] = build_device_analysis(
            "Desktop", recipes, success_metrics, outcome, effect_size, page, feature
        )
    if has_mobile:
        analysis["mobile"] = build_device_analysis(
            "Mobile", recipes, success_metrics, outcome, effect_size, page, feature
        )

    if outcome == "Increased" and flaw_type in ("none", "multiple_metrics"):
        adopted = random.choice([r["recipe"] for r in recipes if r["recipe"] != "Control"])
        recommendation = f"Adopt {adopted}"
        rationale = (
            f"{adopted} showed a statistically significant lift in {success_metrics[0]} "
            f"at the 10% confidence level (p={headline_p}) without negative impact on {guardrail}."
        )
    elif outcome == "Decreased":
        recommendation = "Retain Control"
        rationale = (
            f"Treatment recipe(s) showed a significant decrease in {success_metrics[0]} "
            f"(p={headline_p}). Recommend not shipping."
        )
    elif outcome == "Inconclusive" or flaw_type in ("underpowered", "short_duration"):
        recommendation = "Retain Control"
        rationale = "Results inconclusive given test conditions; recommend rerun with adjusted scope before any rollout decision."
    else:
        recommendation = "Retain Control"
        rationale = (
            f"No statistically significant difference detected at the 10% confidence level "
            f"(p={headline_p}). No business case to ship."
        )

    bias_flags = []
    if flaw_type == "underpowered":
        bias_flags.append({
            "type": "underpowered",
            "detail": (
                f"Required ~{required_n:,} visitors for a {abs(effect_size):.1%} effect at the 10% confidence level "
                f"with 80% power; only {total_visitors:,} visitors used."
            ),
            "severity": "High" if total_visitors < required_n * 0.4 else "Medium",
        })
    if flaw_type == "segment_imbalance":
        control_share = recipes[0]["traffic_split_pct"]
        bias_flags.append({
            "type": "segment_imbalance",
            "detail": (
                f"Control received {control_share}% of traffic vs an expected ~{round(100 / len(recipes), 1)}%. "
                f"Allocation skew may bias results."
            ),
            "severity": "Medium",
        })
    if flaw_type == "short_duration":
        bias_flags.append({
            "type": "novelty_effect_risk",
            "detail": f"Test ran only {duration_days} day(s). Short duration risks novelty effect inflating lift.",
            "severity": "Medium",
        })
    if flaw_type == "multiple_metrics" and len(success_metrics) > 1:
        bias_flags.append({
            "type": "multiple_success_metrics",
            "detail": (
                f"{len(success_metrics)} success metrics declared with no single primary; "
                f"increases risk of post-hoc metric selection."
            ),
            "severity": "Low",
        })

    return {
        "test_id": test_id,
        "uuid": str(uuid.uuid4()),
        "title": f"{page} — {feature} ({success_metrics[0]}) [{product_line}]",
        "product_line": product_line,
        "page": page,
        "feature_tested": feature,
        "test_overview": {
            "hypothesis": hypothesis,
            "problem_statement": problem_statement,
            "critical_questions": critical_questions,
            "success_metrics": success_metrics,
        },
        "custom_metrics": custom_metrics,
        "guardrail_metric": guardrail,
        "recipes": recipes,
        "lifecycle": {
            "test_assignment_date": assignment_date.strftime("%Y-%m-%d"),
            "ready_for_sqa_date": sqa_date.strftime("%Y-%m-%d"),
            "go_live_date": go_live_date.strftime("%Y-%m-%d"),
            "test_end_date": end_date.strftime("%Y-%m-%d"),
            "deepdive_complete_date": deepdive_date.strftime("%Y-%m-%d"),
            "presented_to_oms_date": om_presentation_date.strftime("%Y-%m-%d"),
            "duration_days": duration_days,
        },
        "stakeholders": {
            "OMs": people("OM", n=random.randint(1, 2)),
            "Developers": people("Developer", n=random.randint(1, 3)),
            "Analysts": people("Analyst", n=1),
            "Focal Points": people("Focal Point", n=1),
        },
        "statistical_summary": {
            "confidence_level": "10%",
            "alpha": 0.10,
            "headline_p_value": headline_p,
            "headline_effect_size_pct": round(effect_size * 100, 2),
            "baseline_rate": baseline_rate,
            "statistical_power_achieved": round(actual_power, 3),
            "required_sample_size": required_n,
            "total_visitors": total_visitors,
            "outcome": outcome,
            "significant_at_10pct": outcome in ["Increased", "Decreased"],
        },
        "analysis": analysis,
        "test_summary": {
            "recommendation": recommendation,
            "rationale": rationale,
        },
        "design_flaw": flaw_type,
        "bias_flags": bias_flags,
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main(n=200):
    Path("data").mkdir(exist_ok=True)

    experiments = []
    seen_ids = set()
    while len(experiments) < n:
        exp = generate_experiment()
        if exp["test_id"] not in seen_ids:
            experiments.append(exp)
            seen_ids.add(exp["test_id"])

    with open(Path("data/experiments.json"), "w") as f:
        json.dump(experiments, f, indent=2)

    metadata = {
        "total_experiments": n,
        "confidence_level": "10% (p < 0.10)",
        "outcome_distribution": {
            o: sum(1 for e in experiments if e["statistical_summary"]["outcome"] == o)
            for o in ["Increased", "Decreased", "Flat", "Inconclusive"]
        },
        "recommendation_distribution": {
            "Retain Control": sum(1 for e in experiments if e["test_summary"]["recommendation"] == "Retain Control"),
            "Adopt Recipe": sum(1 for e in experiments if e["test_summary"]["recommendation"].startswith("Adopt")),
        },
        "product_line_distribution": {
            pl: sum(1 for e in experiments if e["product_line"] == pl) for pl in PRODUCT_LINES
        },
        "flaw_distribution": {
            f: sum(1 for e in experiments if e["design_flaw"] == f)
            for f in ["underpowered", "segment_imbalance", "short_duration", "multiple_metrics", "none"]
        },
        "pages_tested": sorted({e["page"] for e in experiments}),
        "features_tested": sorted({e["feature_tested"] for e in experiments}),
        "date_range": {
            "earliest_assignment": min(e["lifecycle"]["test_assignment_date"] for e in experiments),
            "latest_presentation": max(e["lifecycle"]["presented_to_oms_date"] for e in experiments),
        },
        "experiments_with_bias_flags": sum(1 for e in experiments if e["bias_flags"]),
    }

    with open(Path("data/experiments_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Generated {n} experiments → data/experiments.json")
    print(f"📊 Metadata summary → data/experiments_metadata.json")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main(n=200)
