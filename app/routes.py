import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal, User, WorkoutPlan
from app.gemini_generator import generate_workout_and_tip
from app.updated_plan import update_workout_plan

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_topic_background(goal: str) -> str:
    g = goal.lower()
    if "fat" in g or "loss" in g or "burn" in g:
        return "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=1600&q=80"
    elif "muscle" in g or "strength" in g or "bulk" in g:
        return "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=1600&q=80"
    elif "endurance" in g or "run" in g or "cardio" in g:
        return "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?auto=format&fit=crop&w=1600&q=80"
    elif "yoga" in g or "flex" in g or "stretch" in g:
        return "https://images.unsplash.com/photo-1545205597-3d9d02c29597?auto=format&fit=crop&w=1600&q=80"
    return "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1600&q=80"

# User save helper (SQLite-la user create & commit aaga)
def save_user(user_id: int, name: str, age: int, weight: float, goal: str, intensity: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                name=name,
                age=age,
                weight=weight,
                goal=goal,
                intensity=intensity
            )
            db.add(user)
        else:
            user.name = name
            user.age = age
            user.weight = weight
            user.goal = goal
            user.intensity = intensity
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving user: {e}")
    finally:
        db.close()

# Workout plan save helper
def save_plan(user_id: int, plan: str):
    db = SessionLocal()
    try:
        workout = db.query(WorkoutPlan).filter(WorkoutPlan.id == user_id).first()
        if not workout:
            workout = WorkoutPlan(id=user_id, original_plan=plan, updated_plan=None)
            db.add(workout)
        else:
            workout.original_plan = plan
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving plan: {e}")
    finally:
        db.close()

# Updated feedback plan save helper
def save_updated_plan(user_id: int, updated_plan_text: str):
    db = SessionLocal()
    try:
        workout = db.query(WorkoutPlan).filter(WorkoutPlan.id == user_id).first()
        if workout:
            workout.updated_plan = updated_plan_text
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving updated plan: {e}")
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout_html(
    request: Request,
    username: str = Form(...),
    user_id: int = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...)
):
    save_user(user_id=user_id, name=username, age=age, weight=weight, goal=goal, intensity=intensity)

    plan, nutrition_tip = generate_workout_and_tip(goal=goal, intensity=intensity)
    save_plan(user_id=user_id, plan=plan)

    dynamic_bg = get_topic_background(goal)

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "username": username,
            "user_id": user_id,
            "age": age,
            "weight": weight,
            "goal": goal,
            "intensity": intensity,
            "workout_plan": plan,
            "nutrition_tip": nutrition_tip,
            "bg_url": dynamic_bg,
            "updated": False
        }
    )

@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: int = Form(...),
    feedback: str = Form(...)
):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        workout = db.query(WorkoutPlan).filter(WorkoutPlan.id == user_id).first()

        if not user or not workout:
            return HTMLResponse("<h3>User or Workout Plan not found.</h3>", status_code=404)

        current_plan = workout.updated_plan if workout.updated_plan else workout.original_plan
        revised_plan = update_workout_plan(original_plan=current_plan, user_feedback=feedback)
        
        save_updated_plan(user_id=user_id, updated_plan_text=revised_plan)

        nutrition_tip = f"Stay consistent with hydration, recovery, and adequate rest for {user.goal}."
        dynamic_bg = get_topic_background(user.goal)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "username": user.name,
                "user_id": user.id,
                "age": user.age,
                "weight": user.weight,
                "goal": user.goal,
                "intensity": user.intensity,
                "workout_plan": revised_plan,
                "nutrition_tip": nutrition_tip,
                "bg_url": dynamic_bg,
                "updated": True
            }
        )
    finally:
        db.close()

@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        plans = {p.id: p for p in db.query(WorkoutPlan).all()}
        
        user_data = []
        for u in users:
            user_data.append({
                "user": u,
                "plan": plans.get(u.id)
            })

        return templates.TemplateResponse(
            request=request,
            name="all_users.html",
            context={"users_data": user_data}
        )
    finally:
        db.close()

@router.get("/clear-database")
def clear_database():
    db = SessionLocal()
    try:
        db.query(WorkoutPlan).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/view-all-users", status_code=303)

@router.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def ignore_chrome_devtools():
    return JSONResponse(content={})