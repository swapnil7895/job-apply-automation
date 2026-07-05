import re
import datetime
from difflib import SequenceMatcher

def normalize_text(text: str) -> str:
    """Lowercases, strips punctuation, and removes extra spaces."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_skill_from_text(normalized_text: str, profile: dict) -> str:
    """Attempts to find a matching skill from the profile in the text."""
    skills = profile.get("skills_profile", {})
    if not isinstance(skills, dict):
        return None
    for skill in skills.keys():
        if normalize_text(skill) in normalized_text:
            return skill
    return None

def resolve_intent(question_text: str, field_type: str = "text", options: list = None, profile: dict = None) -> dict:
    """
    Resolves a question to an intent, extracts data from the profile, 
    and returns a structured dictionary:
    {
        "type": "static" | "profile" | "dynamic" | "unknown",
        "answer": <raw string or matched option>,
        "field": <profile field if applicable>,
        "handler": <dynamic handler name if applicable>
    }
    """
    if profile is None:
        profile = {}
    
    q_norm = normalize_text(question_text)
    
    # Define Intents and their keywords based on user provided data
    intents = {
        # Profile / Dynamic fields
        "experience": ["experience in", "years", "how many years", "yr", "yrs", "worked with", "worked on", "expertise", "hands on", "handson", "proficiency", "knowledge"],
        "notice_period": ["notice", "joining", "available", "availability", "start date", "when can you join", "earliest joining", "joining period", "immediate joining"],
        "current_ctc": ["current ctc", "present ctc", "annual salary", "current salary", "fixed salary", "current compensation"],
        "expected_ctc": ["expected ctc", "expected salary", "salary expectation", "expected compensation", "desired salary", "salary negotiable"],
        "current_location": ["current location", "where are you located", "location", "city", "residing", "currently based"],
        "preferred_location": ["preferred location", "preferred city", "desired location", "where would you like to work"],
        "mobile": ["mobile", "phone", "contact number"],
        "last_working_day": ["last working day"],
        
        # Static - Yes
        "legally_authorized": ["legally authorized", "eligible to work", "work authorization", "authorized to work"],
        "background_verification": ["background verification", "background check", "drug screening", "reference check"],
        "nda": ["nda", "confidentiality agreement", "employment agreement"],
        "relocate": ["relocate", "relocation", "move", "transfer", "relocation internationally"],
        "travel": ["travel"],
        "work_model": ["onsite", "hybrid", "remote", "remotely"],
        "shifts": ["rotational shifts", "night shifts"],
        "age_18": ["age above 18", "18 years old", "older than 18"],
        "passport_driving": ["passport", "driving license", "driver license"],
        
        # Static - No
        "sponsorship": ["sponsorship", "require sponsorship", "visa sponsorship"],
        "work_permit": ["work permit required"],
        "government": ["government employee", "worked for government", "government official", "politically exposed person", "pep"],
        "conflict_interest": ["conflict of interest"],
        "relative_working": ["relative working", "know anyone working here"],
        "previously_employed": ["previously employed", "worked for this company before"],
        "criminal": ["criminal conviction", "criminal charges", "convicted"],
        "veteran": ["veteran status", "military veteran"],
        "negative_history": ["non-compete", "non compete", "export control", "bankruptcy", "debarred", "terminated for misconduct"],
        
        # Dynamic / Complex
        "applied_before": ["applied to this company before", "applied before"],
        "interviewed_before": ["interviewed with this company before", "interviewed before"],
        "current_employer": ["current employer", "present employer", "current organization", "present organization", "current company", "present company", "organization", "company", "employer"],
        "previous_employer": ["previous employer", "past employer"],
        "reason_leaving": ["reason for leaving", "why are you leaving"],
        "resume_cover": ["resume upload", "cover letter"],
        "portfolio": ["github", "linkedin", "portfolio", "website", "url"],
        "gender": ["gender", "sex"],
        "disability": ["disability"],
        "country": ["country of work authorization", "country of residence"],
    }
    
    detected_intent = "unknown"
    for intent, keywords in intents.items():
        if any(kw in q_norm for kw in keywords):
            detected_intent = intent
            break
            
    response = {"type": "unknown", "answer": None}
    
    # 1. Resolve Profile / Dynamic fields
    if detected_intent == "experience":
        skill = extract_skill_from_text(q_norm, profile)
        default_exp = str(profile.get("total_exp", profile.get("experience", "5")))
        if skill:
            ans = str(profile.get("skills_profile", {}).get(skill, default_exp))
        else:
            ans = default_exp
        response = {"type": "profile", "field": "experience", "answer": ans}
            
    elif detected_intent == "notice_period":
        response = {"type": "profile", "field": "notice_period", "answer": str(profile.get("notice_period", "30"))}
        
    elif detected_intent == "current_ctc":
        response = {"type": "profile", "field": "current_ctc", "answer": str(profile.get("current_ctc", "16.2"))}
        
    elif detected_intent == "expected_ctc":
        response = {"type": "profile", "field": "expected_ctc", "answer": str(profile.get("expected_ctc", "23"))}
        
    elif detected_intent in ["current_location", "preferred_location"]:
        response = {"type": "profile", "field": "location", "answer": str(profile.get("location", "Pune"))}
        
    elif detected_intent == "last_working_day":
        ans = (datetime.datetime.now() + datetime.timedelta(days=60)).strftime("%d/%m/%Y")
        response = {"type": "profile", "field": "last_working_day", "answer": ans}
        
    elif detected_intent == "mobile":
        response = {"type": "profile", "field": "mobile", "answer": str(profile.get("mobile", ""))}

    elif detected_intent == "portfolio":
        response = {"type": "profile", "field": "linkedin_url", "answer": str(profile.get("linkedin_url", "https://www.linkedin.com/"))}

    # 2. Resolve Static fields
    elif detected_intent in ["legally_authorized", "background_verification", "nda", "relocate", "travel", "work_model", "shifts", "age_18", "passport_driving"]:
        response = {"type": "static", "answer": "Yes"}
        
    elif detected_intent in ["sponsorship", "work_permit", "government", "conflict_interest", "relative_working", "previously_employed", "criminal", "veteran", "negative_history"]:
        response = {"type": "static", "answer": "No"}
        
    elif detected_intent == "gender":
        response = {"type": "static", "answer": "Male"}
        
    elif detected_intent == "disability":
        response = {"type": "static", "answer": "Prefer not to say"}
        
    elif detected_intent == "country":
        response = {"type": "static", "answer": "India"}

    elif detected_intent == "current_employer":
        response = {"type": "static", "answer": "Vigoursoft"}

    # 3. Resolve Dynamic handlers
    elif detected_intent in ["applied_before", "interviewed_before", "previous_employer", "reason_leaving", "resume_cover"]:
        response = {"type": "dynamic", "handler": detected_intent, "answer": "No"} # Default answer for dynamic if not handled
        
    # 4. Fallback raw logic
    else:
        if any(kw in q_norm for kw in ["exp", "year", "how much", "how many"]):
            response = {"type": "profile", "field": "experience", "answer": str(profile.get("total_exp", profile.get("experience", "5")))}
        elif any(kw in q_norm for kw in ["do you", "have you", "are you", "willing", "available", "ready", "do u", "have u", "experience in"]):
            response = {"type": "static", "answer": "Yes"}
        else:
            response = {"type": "unknown", "answer": "Yes"}

    # 5. Format output based on field type and options
    if field_type in ["select", "radio", "checkbox", "options"] and options and response.get("answer"):
        best_opt = find_best_option(response["answer"], options, detected_intent)
        response["answer"] = best_opt
    
    return response

def find_best_option(target_answer: str, options: list, intent: str) -> str:
    """Finds the closest matching string in a list of options."""
    if not options or not target_answer:
        return target_answer
        
    # Standardize target
    t_norm = target_answer.lower().strip()
    
    # 1. Exact or partial substring match
    for opt in options:
        o_norm = opt.lower().strip()
        if t_norm == o_norm or t_norm in o_norm or o_norm in t_norm:
            return opt

    # 2. If it's a number (like experience), extract numbers from options
    if t_norm.isdigit():
        target_num = int(t_norm)
        for opt in options:
            nums = [int(n) for n in re.findall(r'\d+', opt)]
            if len(nums) == 2:
                if min(nums) <= target_num <= max(nums):
                    return opt
            elif len(nums) == 1:
                n = nums[0]
                if any(kw in opt.lower() for kw in ["+", "more", ">", "above"]) and target_num >= n:
                    return opt
                elif any(kw in opt.lower() for kw in ["<", "less", "below"]) and target_num <= n:
                    return opt
                elif target_num == n:
                    return opt
                    
    # 3. Fallback to yes/true matching if intent is yes_no-like
    if t_norm in ["yes", "true", "1"]:
        for opt in options:
            if opt.lower().strip() in ["yes", "true", "1", "agree", "willing", "willing to relocate"]:
                return opt
    elif t_norm in ["no", "false", "0"]:
        for opt in options:
            if opt.lower().strip() in ["no", "false", "0", "decline", "not willing"]:
                return opt
                
    # 4. Difflib similarity fallback
    best_opt = options[0]
    best_score = 0
    for opt in options:
        score = SequenceMatcher(None, t_norm, opt.lower().strip()).ratio()
        if score > best_score:
            best_score = score
            best_opt = opt
            
    return best_opt
