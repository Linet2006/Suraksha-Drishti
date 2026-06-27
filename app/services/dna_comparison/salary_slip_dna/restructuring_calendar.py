from datetime import date

RESTRUCTURING_TRIGGERS = {
    "IT_sector":    [date(2024, 4, 1), date(2024, 10, 1)],
    "MNC":          [date(2024, 1, 1), date(2024, 7, 1)],
    "PSU":          [date(2024, 4, 1)],
    "all":          [date(2024, 2, 1)]  # Budget day
}

def get_tolerance_band(company_type, slip_date):
    triggers = RESTRUCTURING_TRIGGERS.get(company_type, [])
    # Also include the "all" triggers
    all_triggers = triggers + RESTRUCTURING_TRIGGERS.get("all", [])
    
    for trigger in all_triggers:
        # Simplified: using absolute days difference ignoring year for recurring annual triggers
        # For a robust system we'd compare month/day or generate triggers for the current year
        try:
            trigger_this_year = date(slip_date.year, trigger.month, trigger.day)
            days_diff = abs((slip_date - trigger_this_year).days)
            if days_diff <= 60:
                return 0.08  # wider band near restructuring dates
        except ValueError:
            pass # Handle leap years etc if needed

    return 0.03  # normal band
