import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="EduGenie", description="A focused AI learning companion")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)


class QuizRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    count: int = Field(default=5, ge=3, le=10)


class PathRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    weeks: int = Field(default=4, ge=1, le=16)


class SummaryRequest(BaseModel):
    text: str = Field(min_length=30, max_length=12000)


class RecommendationRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    level: str = Field(default="new", pattern="^(new|some|confident)$")
    goal: str = Field(min_length=3, max_length=300)


async def generate(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        result = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are EduGenie, a concise, encouraging educational tutor. Explain accurately at the learner's level. Use plain language."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return result.choices[0].message.content or None
    except Exception:
        return None


def local_answer(question: str) -> str:
    lowered = question.lower()
    if "largest ocean" in lowered:
        return "The Pacific Ocean is the largest ocean on Earth. It covers about 165 million square kilometres, nearly one-third of the planet's surface."
    if "pythag" in lowered or "right triangle" in lowered:
        return "The Pythagorean theorem says that for a right triangle, the squares of the two shorter sides add up to the square of the longest side: a² + b² = c². For example, sides 3 and 4 give a hypotenuse of 5, because 9 + 16 = 25."
    if "river" in lowered and "ocean" in lowered:
        return "An ocean is a vast body of salty water, while a river is flowing freshwater that travels through a channel toward a lake, sea, or ocean. Rivers are much smaller, and their water is continually replenished by rain and melting snow."
    return "A good way to start is to identify the key idea, then connect it to an example. Add a little more context to your question and I can give you a more specific explanation."


def local_quiz(topic: str, count: int) -> list[dict[str, Any]]:
    if "pythag" in topic.lower() or "right triangle" in topic.lower():
        questions = [
            {"question": "Which equation represents the Pythagorean theorem?", "options": ["a + b = c", "a² + b² = c²", "a² − b² = c²", "2a + 2b = c"], "answer": 1, "explanation": "For a right triangle, the squares of the two legs add up to the square of the hypotenuse."},
            {"question": "A right triangle has legs of 3 and 4. What is its hypotenuse?", "options": ["5", "6", "7", "12"], "answer": 0, "explanation": "3² + 4² = 9 + 16 = 25, and √25 = 5."},
            {"question": "Which side is called the hypotenuse?", "options": ["The shortest side", "Either side touching the right angle", "The side opposite the right angle", "Any side of equal length"], "answer": 2, "explanation": "The hypotenuse is always opposite the right angle and is the triangle's longest side."},
            {"question": "A right triangle has a hypotenuse of 13 and one leg of 5. What is the other leg?", "options": ["8", "10", "12", "18"], "answer": 2, "explanation": "The missing leg is √(13² − 5²) = √144 = 12."},
            {"question": "Can the theorem be used on a triangle without a right angle?", "options": ["Yes, on every triangle", "No, it applies to right triangles", "Only if all sides match", "Only if one side is 1"], "answer": 1, "explanation": "The Pythagorean theorem specifically describes the side lengths of right triangles."},
        ]
    else:
        questions = [
            {"question": f"What is the best first step when learning {topic}?", "options": ["Memorize every detail", "Identify its core ideas", "Skip examples", "Study advanced topics first"], "answer": 1, "explanation": "A clear grasp of the core ideas makes later details easier to understand."},
            {"question": f"Which approach usually helps you understand {topic} more deeply?", "options": ["Explain it in your own words", "Read without taking breaks", "Avoid asking questions", "Only study definitions"], "answer": 0, "explanation": "Explaining an idea in your own words is a useful way to check understanding."},
            {"question": f"When you get stuck on {topic}, what should you try?", "options": ["Ignore the confusing part", "Break it into smaller steps", "Start over without a goal", "Guess and move on"], "answer": 1, "explanation": "Smaller steps make it easier to locate and work through a difficult idea."},
            {"question": f"Why are examples useful for learning {topic}?", "options": ["They replace all practice", "They connect ideas to concrete cases", "They make concepts less accurate", "They remove the need to review"], "answer": 1, "explanation": "Examples show how an abstract idea can work in a real situation."},
            {"question": f"How can you check your progress in {topic}?", "options": ["Revisit notes only", "Try a new problem without looking at notes", "Avoid practice", "Read the title again"], "answer": 1, "explanation": "Retrieving and applying what you know is a practical check of understanding."},
        ]
    return questions[:count]


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "cloud" if os.getenv("OPENAI_API_KEY") else "local"}


@app.post("/api/ask")
async def ask(request: AskRequest) -> dict[str, str]:
    answer = await generate(f"Answer this learner's question clearly and concisely, with a useful example where appropriate:\n{request.question}")
    return {"answer": answer or local_answer(request.question)}


@app.post("/api/quiz")
async def quiz(request: QuizRequest) -> dict[str, Any]:
    prompt = (
        f"Create {request.count} multiple-choice questions about {request.topic}. "
        "Return only a JSON array. Each object must have question (string), options (array of exactly 4 strings), "
        "answer (zero-based integer index), and explanation (string). Ensure the correct answer is accurate."
    )
    generated = await generate(prompt)
    if generated:
        try:
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", generated.strip())
            items = json.loads(cleaned)
            if isinstance(items, list) and len(items) >= request.count and all(
                isinstance(item.get("question"), str)
                and isinstance(item.get("options"), list)
                and len(item["options"]) == 4
                and isinstance(item.get("answer"), int)
                and 0 <= item["answer"] < 4
                and isinstance(item.get("explanation"), str)
                for item in items[:request.count]
            ):
                return {"topic": request.topic, "questions": items[:request.count]}
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return {"topic": request.topic, "questions": local_quiz(request.topic, request.count)}


@app.post("/api/learning-path")
async def learning_path(request: PathRequest) -> dict[str, str]:
    result = await generate(
        f"Create a practical {request.weeks}-week learning path for {request.topic}, from beginner to advanced. "
        "Include weekly topics, a small hands-on exercise each week, and a few resource suggestions by type. "
        "Format as concise Markdown."
    )
    if result:
        return {"path": result}
    weeks = [
        ("Foundations", "Learn the core vocabulary and mental model. Try a short guided tutorial and write down five key terms."),
        ("Core skills", "Practice the most common concepts with small exercises. Build a tiny example and explain each step."),
        ("Applied practice", "Combine concepts in a realistic mini-project. Use documentation to answer questions as they arise."),
        ("Independent work", "Explore an advanced topic, complete a project, and review what you would improve next."),
    ]
    plan = []
    for index in range(request.weeks):
        title, detail = weeks[min(index * len(weeks) // request.weeks, len(weeks) - 1)]
        plan.append(f"### Week {index + 1}: {title}\n{detail}")
    return {"path": "\n\n".join(plan) + "\n\n**Suggested resources:** an introductory course, the official documentation, and a project-based practice guide."}


@app.post("/api/recommend")
async def recommend(request: RecommendationRequest) -> dict[str, str]:
    result = await generate(
        f"Recommend the next three study actions for a learner studying {request.topic}. "
        f"Their current level is {request.level} and their goal is: {request.goal}. "
        "Make the actions specific, ordered, and achievable this week. Format as concise Markdown."
    )
    if result:
        return {"recommendations": result}
    level_advice = {
        "new": "Start with the core vocabulary and one beginner-friendly explanation.",
        "some": "Review the concepts you already know, then focus on one gap with guided practice.",
        "confident": "Move into a realistic project and examine an advanced use case.",
    }
    return {
        "recommendations": (
            f"1. **Build toward your goal:** {request.goal}. Choose one small task in {request.topic} you can finish this week.\n"
            f"2. **Match your level:** {level_advice[request.level]}\n"
            f"3. **Check your understanding:** explain the result in your own words, then try a fresh example without notes."
        )
    }


@app.post("/api/summarize")
async def summarize(request: SummaryRequest) -> dict[str, str]:
    result = await generate(
        "Summarize this educational passage in plain language. Give a one-sentence overview followed by 3 concise key takeaways.\n\n"
        + request.text
    )
    if result:
        return {"summary": result}
    sentences = re.split(r"(?<=[.!?])\s+", request.text.strip())
    summary = " ".join(sentences[: min(3, len(sentences))])
    if len(summary) > 700:
        summary = summary[:697].rsplit(" ", 1)[0] + "..."
    return {"summary": summary}
