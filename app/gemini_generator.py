import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_fallback_routine(goal: str, intensity: str) -> tuple[str, str]:
    """Reliable fallback if Google free tier servers experience temporary 503 load spikes."""
    tip = (
        f"For {goal}, prioritize lean proteins (eggs, chicken, lentils, or tofu), complex carbohydrates, "
        "and drink at least 2.5–3 liters of water daily. Ensure 7–8 hours of restful sleep for recovery."
    )
    plan = f"""### 7-Day Workout Routine ({goal.title()} - {intensity.title()} Intensity)

* **Day 1: Full-Body Conditioning**
  - Warm-up: 5 mins light jogging & dynamic stretches
  - Bodyweight Squats / Goblet Squats: 3 sets x 12 reps
  - Push-ups (Standard or Incline): 3 sets x 10 reps
  - Plank: 3 sets x 30-45 seconds
  - Cool-down: 5 mins static stretching

* **Day 2: Cardio & Core Activation**
  - Jumping Jacks: 3 sets x 40 seconds
  - Mountain Climbers: 3 sets x 30 seconds
  - Bicycle Crunches: 3 sets x 15 reps per side
  - 20-30 mins brisk walking or light jogging

* **Day 3: Lower Body & Glutes**
  - Lunges (Alternating): 3 sets x 10 reps per leg
  - Glute Bridges: 3 sets x 15 reps
  - Wall Sit: 3 sets x 30 seconds
  - Calf Raises: 3 sets x 20 reps

* **Day 4: Active Recovery & Mobility**
  - 30 mins light outdoor walk
  - Full-body yoga or deep hamstring/hip flexor stretching

* **Day 5: Upper Body & Core Strength**
  - Dumbbell Rows / Resistance Band Rows: 3 sets x 12 reps
  - Pike Push-ups or Shoulder Taps: 3 sets x 10 reps
  - Russian Twists: 3 sets x 20 total twists
  - Superman Holds: 3 sets x 12 reps

* **Day 6: High-Intensity Interval / Circuit**
  - Circuit (3 rounds, 45s work / 15s rest):
    1. High Knees
    2. Bodyweight Squats
    3. Shadow Boxing or Jump Rope
    4. Side Planks (20s each side)

* **Day 7: Rest & System Reset**
  - Complete rest day, hydration focus, and recovery meal prep."""
    return plan, tip

def generate_workout_and_tip(goal: str, intensity: str) -> tuple[str, str]:
    prompt = f"""
You are an expert fitness coach and sports nutritionist.
Target Goal: {goal}
Intensity Level: {intensity}

Provide a structured, comprehensive plan formatted strictly with these exact markers:

===NUTRITION_TIP===
(Write 2-3 sentences of targeted nutrition advice for this goal)

===WORKOUT_PLAN===
(Write a detailed 7-day workout routine with sets, reps, and rest days)
"""
    # Disable automatic tool calling overhead and configure clean text output
    config = types.GenerateContentConfig(
        tools=[]
    )

    # Retry loop with exponential backoff for 503 high demand
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=config
            )
            raw_text = response.text.strip()
            
            if "===WORKOUT_PLAN===" in raw_text:
                parts = raw_text.split("===WORKOUT_PLAN===")
                tip = parts[0].replace("===NUTRITION_TIP===", "").strip()
                plan = parts[1].strip()
                return plan, tip
            
            return raw_text, f"Focus on whole food nutrition and adequate hydration for {goal}."

        except Exception as e:
            err_str = str(e)
            # If Google API servers are experiencing temporary spikes, wait and retry
            if ("503" in err_str or "429" in err_str) and attempt < 3:
                time.sleep(3 * (attempt + 1))  # 3s, 6s, 9s backoff
                continue
            
            # If Google remains 503 unavailable, deliver verified fallback routine
            return get_fallback_routine(goal, intensity)