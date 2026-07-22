import json
import os
import secrets
from random import SystemRandom

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel


app = FastAPI(title="Mira Lenormand API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 测试阶段；正式上线时再改为前端域名
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rng = SystemRandom()
sessions = {}

CARDS = [
    {"number": 1, "name": "骑士", "symbol": "♞", "keyword": "消息、行动、到来"},
    {"number": 2, "name": "三叶草", "symbol": "♣", "keyword": "机会、短暂、轻盈"},
    {"number": 3, "name": "船", "symbol": "⛵", "keyword": "距离、探索、变化"},
    {"number": 4, "name": "房子", "symbol": "⌂", "keyword": "家庭、稳定、安全感"},
    {"number": 5, "name": "树", "symbol": "♧", "keyword": "成长、根基、耐心"},
    {"number": 6, "name": "云", "symbol": "☁", "keyword": "困惑、不确定、遮蔽"},
    {"number": 7, "name": "蛇", "symbol": "♠", "keyword": "复杂、迂回、欲望"},
    {"number": 8, "name": "棺材", "symbol": "▰", "keyword": "结束、停滞、转化"},
    {"number": 9, "name": "花束", "symbol": "✿", "keyword": "喜悦、礼物、吸引"},
    {"number": 10, "name": "镰刀", "symbol": "⚔", "keyword": "突然、决定、切断"},
    {"number": 11, "name": "鞭", "symbol": "〰", "keyword": "争执、反复、压力"},
    {"number": 12, "name": "鸟", "symbol": "♬", "keyword": "交流、焦虑、对话"},
    {"number": 13, "name": "孩子", "symbol": "◌", "keyword": "开始、单纯、新鲜感"},
    {"number": 14, "name": "狐狸", "symbol": "♜", "keyword": "谨慎、策略、观察"},
    {"number": 15, "name": "熊", "symbol": "⬟", "keyword": "力量、资源、掌控"},
    {"number": 16, "name": "星星", "symbol": "✦", "keyword": "希望、指引、愿景"},
    {"number": 17, "name": "鹳", "symbol": "🕊", "keyword": "改变、更新、迁移"},
    {"number": 18, "name": "狗", "symbol": "🐕", "keyword": "朋友、信任、支持"},
    {"number": 19, "name": "塔", "symbol": "♜", "keyword": "距离、边界、独处"},
    {"number": 20, "name": "花园", "symbol": "✾", "keyword": "社交、公开、群体"},
    {"number": 21, "name": "山", "symbol": "▲", "keyword": "阻碍、延迟、坚持"},
    {"number": 22, "name": "道路", "symbol": "↔", "keyword": "选择、分岔、路径"},
    {"number": 23, "name": "老鼠", "symbol": "⌁", "keyword": "消耗、焦虑、流失"},
    {"number": 24, "name": "心", "symbol": "♥", "keyword": "爱、情感、真心"},
    {"number": 25, "name": "戒指", "symbol": "◯", "keyword": "关系、承诺、循环"},
    {"number": 26, "name": "书", "symbol": "▤", "keyword": "未知、秘密、学习"},
    {"number": 27, "name": "信", "symbol": "✉", "keyword": "消息、表达、文件"},
    {"number": 28, "name": "男人", "symbol": "♂", "keyword": "男性、主动能量、当事人"},
    {"number": 29, "name": "女人", "symbol": "♀", "keyword": "女性、感受、当事人"},
    {"number": 30, "name": "百合", "symbol": "⚜", "keyword": "成熟、平静、时间"},
    {"number": 31, "name": "太阳", "symbol": "☀", "keyword": "成功、清晰、活力"},
    {"number": 32, "name": "月亮", "symbol": "☾", "keyword": "情绪、直觉、认可"},
    {"number": 33, "name": "钥匙", "symbol": "⚿", "keyword": "答案、确定、开启"},
    {"number": 34, "name": "鱼", "symbol": "≈", "keyword": "资源、流动、自由"},
    {"number": 35, "name": "锚", "symbol": "⚓", "keyword": "稳定、坚持、停留"},
    {"number": 36, "name": "十字架", "symbol": "✚", "keyword": "压力、课题、承担"},
]

RELATIONSHIP_POSITIONS = ["关系底色", "表层表现", "核心态度", "深层心理", "后续走向"]

MIRA_SYSTEM_PROMPT = """
你是一位叫 Mira 的中文雷诺曼牌解读师。你的风格温和、具体、清晰，帮助用户理解当前关系或问题的趋势，但不把占卜说成绝对事实，也不做医疗、法律、财务等专业结论。

请严格根据用户问题、主题、牌阵位置和抽到的雷诺曼牌进行解读。避免把雷诺曼牌称为塔罗牌；避免夸张恐吓、宿命论或保证结果。
""".strip()


class SessionRequest(BaseModel):
    topic: str
    question: str


class DrawRequest(BaseModel):
    positions: list[int]


class FollowUpRequest(BaseModel):
    topic: str
    original_question: str
    cards: list[dict]
    history: list[dict]
    message: str


def get_ai_client() -> OpenAI:
    api_key = os.getenv("HUNYUAN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="服务器尚未配置 HUNYUAN_API_KEY。")

    return OpenAI(
        api_key=api_key,
        base_url="https://tokenhub.tencentmaas.com/v1",
    )


def clean_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def card_lines_for(topic: str, cards: list[dict]) -> str:
    lines = []
    for index, card in enumerate(cards):
        position_name = (
            RELATIONSHIP_POSITIONS[index]
            if topic == "感情" and index < len(RELATIONSHIP_POSITIONS)
            else f"位置 {index + 1}"
        )
        lines.append(
            f"{position_name}：{card.get('name', '未知')}（关键词：{card.get('keyword', '未提供')}）"
        )
    return "\n".join(lines)


def generate_interpretation(session: dict, cards: list[dict]) -> dict:
    system_prompt = MIRA_SYSTEM_PROMPT + """

必须只返回一个可被程序读取的 JSON 对象，不能使用 Markdown，也不能在 JSON 前后添加任何解释。JSON 必须包含以下四个字段：
{
  "overall": "整体牌意，约 100～180 字",
  "core": "指出最关键的关系动力或矛盾，约 80～140 字",
  "advice": "给用户可执行、尊重边界的建议，约 80～140 字",
  "conclusion": "简洁总结趋势与下一步，约 60～100 字"
}
""".strip()

    user_prompt = f"""
主题：{session['topic']}
用户问题：{session['question']}

本次牌阵：
{card_lines_for(session['topic'], cards)}

请生成本次完整解读。
""".strip()

    try:
        completion = get_ai_client().chat.completions.create(
            model="hy3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        interpretation = clean_json(completion.choices[0].message.content or "")
        required_fields = ["overall", "core", "advice", "conclusion"]
        if not all(interpretation.get(field) for field in required_fields):
            raise ValueError("模型返回内容缺少必要字段。")
        return interpretation
    except HTTPException:
        raise
    except Exception as error:
        print(f"AI interpretation error: {error}")
        raise HTTPException(status_code=502, detail="AI 解读暂时生成失败，请稍后重新抽牌。")


def generate_follow_up(payload: FollowUpRequest) -> str:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="追问内容不能为空。")
    if len(message) > 600:
        raise HTTPException(status_code=400, detail="追问请控制在 600 字以内。")

    history_messages = []
    for item in payload.history[-8:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            history_messages.append({"role": role, "content": content[:1600]})

    context = f"""
这是对同一次雷诺曼占卜的继续追问。
主题：{payload.topic}
最初问题：{payload.original_question}
固定牌阵：
{card_lines_for(payload.topic, payload.cards)}

请围绕这次固定牌阵和已有对话回应追问；不要重新抽牌，不要假装拥有未提供的信息。回答应温和、具体、可执行，约 120～220 字。
""".strip()

    try:
        completion = get_ai_client().chat.completions.create(
            model="hy3",
            messages=[
                {"role": "system", "content": MIRA_SYSTEM_PROMPT},
                {"role": "user", "content": context},
                *history_messages,
                {"role": "user", "content": message},
            ],
            temperature=0.7,
        )
        reply = (completion.choices[0].message.content or "").strip()
        if not reply:
            raise ValueError("模型没有返回追问回答。")
        return reply
    except HTTPException:
        raise
    except Exception as error:
        print(f"AI follow-up error: {error}")
        raise HTTPException(status_code=502, detail="AI 追问暂时生成失败，请稍后再试。")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/sessions")
def create_session(payload: SessionRequest):
    topic = payload.topic.strip()
    question = payload.question.strip()
    if not topic or not question:
        raise HTTPException(status_code=400, detail="主题和问题不能为空。")

    draw_count = 5 if topic == "感情" else 3
    session_id = secrets.token_urlsafe(16)
    sessions[session_id] = {
        "topic": topic,
        "question": question,
        "draw_count": draw_count,
        "shuffled_cards": [],
    }
    return {"session_id": session_id, "topic": topic, "question": question, "draw_count": draw_count}


@app.post("/api/sessions/{session_id}/shuffle")
def shuffle_cards(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已失效，请重新开始。")

    shuffled_cards = CARDS.copy()
    rng.shuffle(shuffled_cards)
    session["shuffled_cards"] = shuffled_cards
    return {"session_id": session_id, "message": "洗牌完成", "card_count": len(shuffled_cards)}


@app.post("/api/sessions/{session_id}/draw")
def draw_cards(session_id: str, payload: DrawRequest):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已失效，请重新开始。")
    if not session["shuffled_cards"]:
        raise HTTPException(status_code=400, detail="请先完成洗牌。")

    positions = payload.positions
    if len(positions) != session["draw_count"]:
        raise HTTPException(status_code=400, detail=f"本次需要选择 {session['draw_count']} 个数字。")
    if len(set(positions)) != len(positions):
        raise HTTPException(status_code=400, detail="数字不能重复。")
    if any(position < 1 or position > 36 for position in positions):
        raise HTTPException(status_code=400, detail="数字必须在 1 到 36 之间。")

    cards = []
    for position in positions:
        card = session["shuffled_cards"][position - 1].copy()
        card["draw_position"] = position
        cards.append(card)

    interpretation = generate_interpretation(session, cards)
    return {
        "question": session["question"],
        "topic": session["topic"],
        "cards": cards,
        "interpretation": interpretation,
    }


@app.post("/api/follow-up")
def follow_up(payload: FollowUpRequest):
    return {"reply": generate_follow_up(payload)}
