# ------------------------ CGPA scale ------------------------
CGPA_MIN, CGPA_MAX = 0.0, 4.0        
GRADE_STEP = 0.33                    

# ------------------- Domain A: probation and drop -------------------
PROBATION_MIN_CGPA = 2.0             
DROP_AFTER_PROBATIONS = 2            
PROBATION_COUNTS = (0, 1, 2)    

# --- Domain B: scholarship retention ---
# Non-engineering programmes only.
SCHOLARSHIP_THRESHOLDS = {
    "merit_batch_topper": 3.75,        
    "advance_merit_continuation": 3.50,  
    "financial_assistance": 2.50,        
}
SCHOLARSHIP_LABELS = {
    "merit_batch_topper": "Merit scholarship (batch topper)",
    "advance_merit_continuation": "Advance merit scholarship (continuation)",
    "financial_assistance": "Financial assistance scholarship (FAS)",
}

# --- Credit load (used as an input to Domain B) ---
CREDITS_MIN = 9                      
CREDITS_MAX = 18                    
CREDIT_STEP = 3                      

# --- Output variable ---
RISK_UNIVERSE = (0, 100)
RISK_TERMS = ("low", "moderate", "high", "critical")   # ordered by severity

# --- Numerical resolution ---
CGPA_RESOLUTION = 0.01
CREDIT_RESOLUTION = 0.5
RISK_RESOLUTION = 1


