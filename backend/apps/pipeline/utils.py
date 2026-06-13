import json
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def analyze_business_presence(business):
    """
    Analyzes a business's digital presence using GPT-4o.
    Returns a score (0-100) and analysis notes.
    """
    prompt = f"""
    Analyze the digital presence of this business and identify growth opportunities for a web/app development agency.
    
    Business Name: {business.name}
    Category: {business.category}
    Location: {business.location}
    Has Website: {business.has_website}
    Website URL: {business.website_url or 'None'}
    Has Booking System: {business.has_booking_system}
    Google Rating: {business.google_rating or 'N/A'}
    
    Output JSON exactly in this format:
    {{
        "score": <integer 0-100 based on digital maturity>,
        "strengths": ["...", "..."],
        "weaknesses": ["...", "..."],
        "opportunities": ["...", "..."]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a digital presence analyst for a web development agency."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI Analysis Error: {e}")
        return {"score": 50, "strengths": [], "weaknesses": ["Could not analyze properly"], "opportunities": ["Needs digital review"]}


def generate_outreach_email(business):
    """
    Generates a personalized cold email using GPT-4o.
    """
    prompt = f"""
    You are an advanced autonomous AI Sales Development Representative (AI SDR) designed to help a web development and mobile app agency acquire new clients. Your primary responsibility is to research local businesses, analyze their digital presence, and generate highly personalized cold outreach messages offering website development, mobile app development, booking systems, and digital growth solutions.

    Business Profile:
    - Name: {business.name}
    - Type: {business.category}
    - Location: {business.location}
    - Has Website: {business.has_website}
    - Has Booking System: {business.has_booking_system}
    - Digital Score: {business.digital_score}/100
    - Analysis Notes: {json.dumps(business.analysis_notes)}
    
    Agency Info (Use softly if needed):
    - Name: {settings.AGENCY_NAME}
    - Website: {settings.AGENCY_WEBSITE}

    RULES:
    1. Email must be extremely short and focused (between 80–120 words). Real humans do not write long essays.
    2. Subject must be short, casual, and highly personal (max 6-8 words, e.g., "quick question regarding {business.name}" or "noticed your site in {business.location}"). BANNED: Banal marketing subjects or all-capitalized subject lines.
    3. GREETINGS & OPENINGS: Absolutely BANNED from starting with "Dear [Name]," "I hope this email finds you well," "I hope you are doing great," or "My name is...". Instead, start directly, warmly, and casually, like: "Hi [Name]," or "Hey [Name],". The very next sentence must immediately jump to a specific observation about their business website or location so it reads like a real human junior outreach note.
    4. BANNED AI BUZZWORDS: Under no circumstances are you allowed to use any of these typical ChatGPT/AI copywriting words: "delighted", "moreover", "testament", "revolutionize", "leverage", "robust", "optimize", "streamline", "cutting-edge", "pioneering", "thrilled", "excited", "scale", "landscape", "furthermore", "in today's digital age", "look no further", "top-notch", "game-changer", "bespoke", "tailor-made", "synergistic", "transform".
    5. Tone must be warm, direct, conversational, and highly personal. Write exactly like a busy junior partner writing a quick note. Keep sentences simple and punchy.
    6. Always include business name naturally.
    7. Always include a soft, non-salesy call-to-action (e.g. "Open to a quick chat next week?", "No pressure at all, just let me know if you're open to a brief call.").
    8. Never mention AI, SDRs, automation, or algorithms. Focus strictly on a single growth value point identified in the digital scorecard.

    Output ONLY valid JSON:
    {{
        "subject": "string",
        "email": "string"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert cold email copywriter."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI Email Gen Error: {e}")
        return {"subject": f"Quick question regarding {business.name}", "email": "Hi, I noticed your business and would love to help you grow your digital presence. Let me know if you're open to a chat."}
