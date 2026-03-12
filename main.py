import os
from fastapi import FastAPI, BackgroundTasks, Request
import swisseph as swe
import stripe
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

# --- НАСТРОЙКИ ---
stripe.api_key = "sk_test_..." # Ваш ключ Stripe
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 465,
    "user": "your@email.com",
    "pass": "your_app_password"
}

# --- ЛОГИКА РАСЧЕТА ---
def get_hd_data(birth_date, birth_time):
    # Упрощенный расчет для примера (здесь используем функции из прошлых ответов)
    # 1. Расчет планет через swe.calc_ut
    # 2. Определение ворот и линий
    # 3. Поиск точки дизайна (-88 градусов)
    # Для примера возвращаем заглушку:
    return {
        "type": "Generator",
        "authority": "Sacral",
        "profile": "4/6"
    }

# --- ГЕНЕРАТОР ТЕКСТА ---
def create_report(hd_results):
    templates = {
        "Generator": "Вы — Генератор. Ваша сила в отклике...",
        "Sacral": "Ваш авторитет Сакральный: слушайте звуки своего тела.",
    }
    report = f"Ваш тип: {hd_results['type']}\n"
    report += f"Ваш авторитет: {hd_results['authority']}\n\n"
    report += templates.get(hd_results['type'], "")
    return report

# --- ПОЧТОВАЯ СЛУЖБА ---
def send_email(email, content):
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = 'Ваш расчет Дизайна Человека'
    msg['From'] = SMTP_CONFIG["user"]
    msg['To'] = email
    with smtplib.SMTP_SSL(SMTP_CONFIG["server"], SMTP_CONFIG["port"]) as server:
        server.login(SMTP_CONFIG["user"], SMTP_CONFIG["pass"])
        server.send_message(msg)

# --- ЭНДПОИНТЫ (API) ---
class UserData(BaseModel):
    name: str
    email: str
    birth_date: str # ГГГГ-ММ-ДД
    birth_time: str # ЧЧ:ММ
    city: str

@app.post("/create-calculation")
async def create_calc(user: UserData):
    # 1. Считаем данные сразу (но не отдаем до оплаты)
    results = get_hd_data(user.birth_date, user.birth_time)
    
    # 2. Создаем сессию оплаты в Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f'Расчет для {user.name}'},
                'unit_amount': 2000, # $20.00
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url="https://your-site.com",
        metadata={
            "email": user.email,
            "hd_type": results["type"],
            "hd_auth": results["authority"]
        }
    )
    return {"checkout_url": session.url}

@app.post("/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    # В реальном проекте здесь нужна проверка подписи Stripe!
    event = stripe.Event.construct_from(eval(payload), stripe.api_key)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        email = session.metadata.get("email")
        hd_data = {
            "type": session.metadata.get("hd_type"),
            "authority": session.metadata.get("hd_auth")
        }
        
        # Генерируем и отправляем отчет в фоновом режиме
        report = create_report(hd_data)
        background_tasks.add_task(send_email, email, report)
        
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)