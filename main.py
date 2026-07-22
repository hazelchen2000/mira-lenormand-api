import secrets
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Mira Lenormand API")

# 当前为前后端联调阶段，先允许网页调用。
# 正式上线后，会替换为你的前端网址。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

CARDS = [
    {"number": 1, "name": "骑士", "symbol": "♞", "keyword": "消息、推进、到来"},
    {"number": 2, "name": "三叶草", "symbol": "☘", "keyword": "机会、短暂、轻盈"},
    {"number": 3, "name": "船", "symbol": "⛵", "keyword": "远行、推进、变化"},
    {"number": 4, "name": "房屋", "symbol": "⌂", "keyword": "稳定、家庭、边界"},
    {"number": 5, "name": "树", "symbol": "♧", "keyword": "成长、根基、耐心"},
    {"number": 6, "name": "云", "symbol": "☁", "keyword": "不明、摇摆、遮蔽"},
    {"number": 7, "name": "蛇", "symbol": "〰", "keyword": "复杂、绕路、策略"},
    {"number": 8, "name": "棺材", "symbol": "▭", "keyword": "结束、停滞、转折"},
    {"number": 9, "name": "花束", "symbol": "✿", "keyword": "好意、礼物、缓和"},
    {"number": 10, "name": "镰刀", "symbol": "⌒", "keyword": "切断、突然、决断"},
    {"number": 11, "name": "鞭", "symbol": "⌁", "keyword": "争执、反复、压力"},
    {"number": 12, "name": "鸟", "symbol": "◜", "keyword": "沟通、焦虑、讨论"},
    {"number": 13, "name": "孩童", "symbol": "◌", "keyword": "新事物、起步"},
    {"number": 14, "name": "狐狸", "symbol": "◇", "keyword": "策略、谨慎、伪装"},
    {"number": 15, "name": "熊", "symbol": "⬟", "keyword": "力量、资源、掌控"},
    {"number": 16, "name": "星星", "symbol": "✦", "keyword": "希望、指引、远景"},
    {"number": 17, "name": "鹳", "symbol": "⌁", "keyword": "迁移、改善、变化"},
    {"number": 18, "name": "狗", "symbol": "●", "keyword": "忠诚、朋友、支持"},
    {"number": 19, "name": "塔", "symbol": "▥", "keyword": "距离、制度、隔离"},
    {"number": 20, "name": "花园", "symbol": "✾", "keyword": "社交、公开、群体"},
    {"number": 21, "name": "山", "symbol": "△", "keyword": "阻碍、延迟、困难"},
    {"number": 22, "name": "道路", "symbol": "⌯", "keyword": "选择、分岔、路径"},
    {"number": 23, "name": "老鼠", "symbol": "…", "keyword": "消耗、焦虑、流失"},
    {"number": 24, "name": "心", "symbol": "♥", "keyword": "情感、喜欢、真心"},
    {"number": 25, "name": "指环", "symbol": "○", "keyword": "承诺、关系、循环"},
    {"number": 26, "name": "书", "symbol": "▤", "keyword": "未知、秘密、学习"},
    {"number": 27, "name": "信", "symbol": "✉", "keyword": "文本、通知、结果"},
    {"number": 28, "name": "男人", "symbol": "♂", "keyword": "主动方、当事人"},
    {"number": 29, "name": "女人", "symbol": "♀", "keyword": "接收方、当事人"},
    {"number": 30, "name": "百合", "symbol": "⚜", "keyword": "成熟、平静、长期"},
    {"number": 31, "name": "太阳", "symbol": "☉", "keyword": "成功、清晰、能量"},
    {"number": 32, "name": "月亮", "symbol": "☾", "keyword": "情绪、感受、名望"},
    {"number": 33, "name": "钥匙", "symbol": "⚿", "keyword": "关键、确定、打开"},
    {"number": 34, "name": "鱼", "symbol": "≈", "keyword": "流动、金钱、资源"},
    {"number": 35, "name": "船锚", "symbol": "⚓", "keyword": "稳定、长期、落地"},
    {"number": 36, "name": "十字架", "symbol": "✛", "keyword": "压力、课题、负担"},
]

sessions = {}


class SessionRequest(BaseModel):
    topic: str
    question: str


class DrawRequest(BaseModel):
    positions: list[int]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/sessions")
def create_session(data: SessionRequest):
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="请输入占卜问题")

    draw_count = 5 if data.topic == "感情" else 3
    session_id = secrets.token_urlsafe(16)

    sessions[session_id] = {
        "topic": data.topic,
        "question": data.question.strip(),
        "draw_count": draw_count,
        "deck": None,
    }

    return {
        "session_id": session_id,
        "draw_count": draw_count,
        "spread": "五张关系态度阵" if draw_count == 5 else "线性三张牌阵",
    }


@app.post("/api/sessions/{session_id}/shuffle")
def shuffle(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="本次占卜不存在或已失效")

    deck = list(range(1, 37))
    random.SystemRandom().shuffle(deck)
    session["deck"] = deck

    return {
        "message": "已洗牌",
        "draw_count": session["draw_count"],
    }


@app.post("/api/sessions/{session_id}/draw")
def draw_cards(session_id: str, data: DrawRequest):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="本次占卜不存在或已失效")

    if session["deck"] is None:
        raise HTTPException(status_code=400, detail="请先洗牌")

    positions = data.positions

    if len(positions) != session["draw_count"]:
        raise HTTPException(
            status_code=400,
            detail=f"本次牌阵需要选择 {session['draw_count']} 个数字",
        )

    if len(set(positions)) != len(positions):
        raise HTTPException(status_code=400, detail="数字不能重复")

    if any(position < 1 or position > 36 for position in positions):
        raise HTTPException(status_code=400, detail="数字必须在 1 到 36 之间")

    cards = []
    for position in positions:
        card_number = session["deck"][position - 1]
        card = next(card for card in CARDS if card["number"] == card_number)
        cards.append({**card, "draw_position": position})

    return {
        "question": session["question"],
        "topic": session["topic"],
        "cards": cards,
        "interpretation": {
            "overall": "这是当前测试阶段的模拟解读。正式版本会由你的雷诺曼 skill 根据问题、牌阵与真实牌面生成完整分析。",
            "core": "牌阵已经由后端真实洗牌，并按照用户选择的位置翻开。",
            "advice": "先观察牌面关键词与现实中的具体讯号，再决定下一步行动。",
            "conclusion": "本次牌面呈现的是趋势和可参考的方向。",
        },
    }
