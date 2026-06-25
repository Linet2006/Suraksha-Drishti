COMPANY_PROFILES = {
    "TCS": {
        "basic_pct_range": (0.38, 0.44),
        "pf_on_cap": True,          # PF on ₹15,000, not full basic
        "increment_month": 10,       # October
        "employee_id_pattern": r'^\d{8}$',
        "zero_style": "–",
        "known_cities": ["bengaluru","chennai","hyderabad","pune","mumbai"]
    },
    "Infosys": {
        "basic_pct_range": (0.40, 0.48),
        "pf_on_cap": True,
        "increment_month": 4,
        "employee_id_pattern": r'^\d{7}$',
    },
    "Canara Bank": {
        "basic_pct_range": (0.45, 0.55),
        "da_expected": True,         # PSU — DA component exists
        "pay_commission": "7th_CPC"
    }
}
