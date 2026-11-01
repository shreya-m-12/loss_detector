"""
Recommendation generator for detected business loss patterns.
Rule-based templates populated with exact trigger metrics and actionable decision advice.
Strictly follows Section 6 guidelines: (1) what the issue is, (2) why flagged, (3) action to investigate.
Uses transparent phrasing: 'potential', 'flagged', 'investigate'.
"""

def generate_recommendation(rule_code: str, subject_name: str, period_month: str, trigger_values: dict, threshold_info: dict) -> tuple:
    """
    Returns (explanation: str, recommendation: str).
    """
    if rule_code == "R1":
        rev = trigger_values["revenue"]
        cost = trigger_values["cost"]
        loss = trigger_values["loss_amount"]
        margin = trigger_values.get("margin")
        margin_str = f"{margin:.1f}%" if margin is not None else "N/A"
        formula = f"Loss = Cost (₹{cost:,.2f}) - Revenue (₹{rev:,.2f}) = ₹{loss:,.2f} (Margin: {margin_str})"
        
        explanation = (
            f"Flagged potential product loss: '{subject_name}' generated ₹{rev:,.2f} in revenue "
            f"against product acquisition cost of ₹{cost:,.2f} in {period_month}, resulting in a loss of ₹{loss:,.2f} ({formula})."
        )
        recommendation = (
            f"Investigate pricing and procurement for '{subject_name}'. Immediate actions: "
            f"1) Verify supplier invoice prices against recent purchase orders for price inflation. "
            f"2) Review recent promotional or clearance discounts to ensure selling price covers wholesale unit cost. "
            f"3) Renegotiate vendor procurement terms or consider substituting with a higher-margin alternative."
        )
        return explanation, recommendation

    elif rule_code == "R2":
        rev = trigger_values["revenue"]
        cost = trigger_values["cost"]
        profit = trigger_values["profit"]
        margin = trigger_values["margin"]
        max_th = threshold_info.get("max_margin", 10.0)
        formula = f"Margin = ((₹{rev:,.2f} - ₹{cost:,.2f}) / ₹{rev:,.2f}) x 100 = {margin:.1f}%"

        explanation = (
            f"Flagged low-margin product: '{subject_name}' yielded a gross profit margin of {margin:.1f}% "
            f"in {period_month}, which is below the target profitability threshold of {max_th:.0f}% ({formula})."
        )
        recommendation = (
            f"Examine margin structure for '{subject_name}'. Recommended actions: "
            f"1) Explore modest retail price adjustments of 3% to 5% if local competitor pricing allows. "
            f"2) Bundle with complementary higher-margin essentials to raise average basket margin. "
            f"3) Check whether distributor freight or handling surcharges are eating into base margins."
        )
        return explanation, recommendation

    elif rule_code == "R3":
        prev_m = trigger_values["prev_month"]
        prev_q = trigger_values["prev_quantity"]
        curr_q = trigger_values["curr_quantity"]
        pct = trigger_values["pct_change"]
        th_pct = threshold_info.get("threshold_pct", -20.0)
        formula = f"(({curr_q:.1f} - {prev_q:.1f}) / {prev_q:.1f}) x 100 = {pct:.1f}%"

        explanation = (
            f"Flagged significant sales volume decline: sales volume of '{subject_name}' fell from "
            f"{prev_q:.1f} units in {prev_m} to {curr_q:.1f} units in {period_month} ({formula}), "
            f"crossing the decline threshold of {th_pct:.0f}%."
        )
        recommendation = (
            f"Investigate root cause of demand decrease for '{subject_name}'. Recommended steps: "
            f"1) Audit inventory logs for out-of-stock periods during {period_month}. "
            f"2) Benchmark nearby competitor retail prices and promotions. "
            f"3) Evaluate shelf placement, store visibility, and seasonal demand fluctuations."
        )
        return explanation, recommendation

    elif rule_code == "R4":
        prev_m = trigger_values["prev_month"]
        prev_amt = trigger_values["prev_amount"]
        curr_amt = trigger_values["curr_amount"]
        pct = trigger_values["pct_change"]
        th_pct = threshold_info.get("threshold_pct", 30.0)
        formula = f"((₹{curr_amt:,.2f} - ₹{prev_amt:,.2f}) / ₹{prev_amt:,.2f}) x 100 = +{pct:.1f}%"

        explanation = (
            f"Flagged unusual operating expense surge: '{subject_name}' increased from ₹{prev_amt:,.2f} in {prev_m} "
            f"to ₹{curr_amt:,.2f} in {period_month} ({formula}), exceeding the {th_pct:.0f}% surge threshold."
        )
        recommendation = (
            f"Audit operating expense vouchers for '{subject_name}'. Recommended actions: "
            f"1) Check if the increase was caused by a one-time annual payment, seasonal rate hike, or billing anomaly. "
            f"2) Audit utility meters, maintenance contracts, or vendor invoices for unexpected service additions. "
            f"3) Review operational wastage and enforce spending caps."
        )
        return explanation, recommendation

    elif rule_code == "R5":
        inv = trigger_values["inventory_snapshot"]
        avg_q = trigger_values["avg_monthly_sales"]
        ratio = trigger_values["ratio"]
        th_ratio = threshold_info.get("multiple_threshold", 3.0)
        formula = f"{inv:.1f} units / {avg_q:.1f} units/month = {ratio:.1f}x"

        explanation = (
            f"Flagged potential overstock and working capital lockup: '{subject_name}' inventory snapshot of "
            f"{inv:.1f} units as of {period_month} end equals {ratio:.1f}x the trailing 3-month average monthly sales "
            f"of {avg_q:.1f} units ({formula}), exceeding the {th_ratio:.0f}x risk threshold."
        )
        recommendation = (
            f"Mitigate inventory risk and capital holding costs for '{subject_name}': "
            f"1) Temporarily halt or reduce replenishment purchase orders. "
            f"2) Inspect warehouse/shelf stock for perishable expiry dates and packaging condition. "
            f"3) Introduce promotional bundles or targeted volume discounts to accelerate stock liquidation."
        )
        return explanation, recommendation

    elif rule_code == "R6":
        m_before = trigger_values.get("margin_before")
        m_after = trigger_values.get("margin_after")
        drop = trigger_values.get("drop_points")
        th_drop = threshold_info.get("drop_threshold_points", 15.0)
        disc_amt = trigger_values.get("discount_amount", 0.0)

        if m_after is None:
            explanation = (
                f"Flagged extreme discount risk: '{subject_name}' in {period_month} had ₹{disc_amt:,.2f} in discounts "
                f"reducing sales revenue to zero while incurring acquisition cost."
            )
            recommendation = (
                f"Immediately halt 100% discount promotions on '{subject_name}'. Audit cashier overrides "
                f"and verify discount approval controls."
            )
        else:
            formula = f"{m_before:.1f}% (before discount) - {m_after:.1f}% (after discount) = {drop:.1f} points drop"
            explanation = (
                f"Flagged excessive margin erosion from discounts: '{subject_name}' margin fell from {m_before:.1f}% "
                f"to {m_after:.1f}% ({formula}) due to ₹{disc_amt:,.2f} in promotional discounts in {period_month}, "
                f"exceeding the {th_drop:.0f} percentage points threshold."
            )
            recommendation = (
                f"Restructure discount promotions on '{subject_name}': "
                f"1) Cap promotional discount rate to protect a minimum gross profit margin of 15%. "
                f"2) Shift from flat cash discounts to minimum spend thresholds (e.g. buy 2 get 10% off). "
                f"3) Track whether discount volume actually increased total basket size enough to justify margin sacrifice."
            )
        return explanation, recommendation

    return "Alert flagged for review.", "Investigate transaction records."
