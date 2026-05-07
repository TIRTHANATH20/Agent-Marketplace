# Integration Examples

## Slack Integration

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    # Purchase logic
    
    # Notify on Slack
    try:
        slack_client.chat_postMessage(
            channel="#purchases",
            text=f"New purchase by {current_user.email}: Agent {agent_id}"
        )
    except SlackApiError as e:
        logger.error(f"Slack notification failed: {e}")
```

## Webhook Integration

```python
from httpx import AsyncClient

async def send_webhook(event: str, data: dict):
    """Send event to external webhook"""
    async with AsyncClient() as client:
        try:
            await client.post(
                "https://example.com/webhooks/marketplace",
                json={"event": event, "data": data},
                timeout=10
            )
        except Exception as e:
            logger.error(f"Webhook failed: {e}")

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    purchase = create_purchase(agent_id, current_user.id)
    await send_webhook("purchase.created", purchase.dict())
    return purchase
```

## Email Notifications

```python
from fastapi_mail import FastMail, MessageSchema

conf = ConnectionConfig(
    MAIL_FROM="noreply@marketplace.com",
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USERNAME="your-email@gmail.com",
    MAIL_PASSWORD="your-app-password",
    MAIL_TLS=True,
    MAIL_SSL=False,
)

fm = FastMail(conf)

async def send_purchase_email(user_email: str, agent_name: str, token: str):
    message = MessageSchema(
        subject="Purchase Confirmation",
        recipients=[user_email],
        body=f"""
        You successfully purchased {agent_name}!
        
        Access Token: {token}
        
        Use this token to access the agent API.
        """,
        subtype="html"
    )
    await fm.send_message(message)

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    purchase = Purchase(user_id=current_user.id, agent_id=agent_id)
    
    await send_purchase_email(
        current_user.email,
        agent.name,
        purchase.access_token
    )
    
    db.add(purchase)
    db.commit()
    return purchase
```

## OAuth2 Integration (Google)

```python
from google.auth.transport import requests
from google.oauth2 import id_token

async def verify_google_token(token: str) -> dict:
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/google")
async def google_login(token: str):
    idinfo = await verify_google_token(token)
    user = db.query(User).filter(User.email == idinfo['email']).first()
    
    if not user:
        user = User(email=idinfo['email'], full_name=idinfo['name'])
        db.add(user)
        db.commit()
    
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token}
```

## Payment Processing (Stripe)

```python
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

@app.post("/checkout")
async def create_checkout(agent_id: int, current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": agent.name},
                "unit_amount": int(agent.price * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        customer_email=current_user.email,
    )
    
    return {"session_id": session.id}

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.environ["STRIPE_WEBHOOK_SECRET"]
        )
    except ValueError:
        raise HTTPException(status_code=400)
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Create purchase in database
        
    return {"status": "success"}
```

## Monitoring (Datadog)

```python
from datadog import initialize, api
from ddtrace import patch_all

patch_all()

options = {
    "api_key": os.environ["DATADOG_API_KEY"],
    "app_key": os.environ["DATADOG_APP_KEY"]
}
initialize(**options)

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    with datadog_tracer.trace("agent.purchase") as span:
        span.set_tag("agent_id", agent_id)
        span.set_tag("user_id", current_user.id)
        
        purchase = create_purchase(agent_id, current_user.id)
        
        span.set_metric("purchase.value", purchase.amount)
    
    return purchase
```

## Analytics (Amplitude)

```python
from amplitude import Amplitude

amplitude = Amplitude(os.environ["AMPLITUDE_API_KEY"])

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    purchase = create_purchase(agent_id, current_user.id)
    
    amplitude.track(
        event_type="agent_purchased",
        user_id=str(current_user.id),
        event_properties={
            "agent_id": agent_id,
            "price": purchase.amount,
            "timestamp": purchase.purchased_at.isoformat()
        }
    )
    
    return purchase
```

## Message Queue (Celery)

```python
from celery import Celery

celery_app = Celery("marketplace", broker="redis://localhost:6379")

@celery_app.task
def send_purchase_notification(user_email: str, agent_name: str):
    # Send email asynchronously
    send_email(user_email, f"Purchase confirmation: {agent_name}")

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    purchase = create_purchase(agent_id, current_user.id)
    
    # Queue task
    send_purchase_notification.delay(current_user.email, agent.name)
    
    return purchase
```
