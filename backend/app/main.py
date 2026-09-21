from __future__ import annotations
from argon2 import PasswordHasher
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import logging
import sqlite3
from app.db import get_db, row_to_dict, init_db
import urllib.error #should delete?
import urllib.request  #should delete?
from typing import Annotated
import os, json
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, field_validator
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

app = FastAPI(title="Delivery App API") #start a backend server

p = Path(__file__).parent.resolve()
abs = p / '.env'
load_dotenv(abs)

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"), #may change to pathlib?
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

secret_key = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ph = PasswordHasher()

def hash_password(password: str) -> str:
    digest = ph.hash(password)
    return digest

def verify_password(stored: str, password: str) -> bool:
    try:
        return ph.verify(stored, password)
    except:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded

def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidCredentialsError
        user_id = int(user_id)
        if user_id <= 0:
            raise InvalidCredentialsError
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError
    except (InvalidTokenError, ValueError, TypeError):
        raise InvalidCredentialsError
    return user_id

def get_current_user(user_id: Annotated[int, Depends(get_current_user_id)]):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise InvalidCredentialsError  #假如A,B用户均有token，是否可能B用了A的token进入A的用户权限？
    return UserPublic(id=user["id"], name=user["name"], email=user["email"])

@app.on_event("startup")
def startup():
    init_db()

class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=16)
    @field_validator("password")
    @classmethod
    def password_must_have_special_char(cls, value):
        special_characters = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
        if not any(char in special_characters for char in value):
            raise ValueError("Password must contain at least one special character")
        return value

class LoginPayload(BaseModel):
    email: EmailStr = Field(min_length=5, max_length=120)
    password: str

class UserPublic(BaseModel):
    id: int
    name: str
    email: str

class OrderItemPayload(BaseModel):
    food_id: int
    quantity: int = Field(gt=0, le=20)

class OrderPayload(BaseModel):
    items: list[OrderItemPayload] = Field(min_length=1)

class SearchInput(BaseModel):
    user_input: str
class FoodRecommendation(BaseModel):
    food_id:int
    food_name:str
    food_recommend_reason:str
    food_price:float
    food_image:str

class StoreRecommendation(BaseModel):
    store_id:int
    store_name:str
    store_recommend_reason:str
    store_image:str
    rating:float
    delivery_minute:int
    foodlist: list[FoodRecommendation]

class StoresList(BaseModel):
    stores_recommend: list[StoreRecommendation]

class Token(BaseModel):
    access_token: str
    token_type: str

def issue_user_response(user: UserPublic, token: Token):
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "token": token.access_token,
    }

# need to delete
# def current_user(authorization: Annotated[str | None, Header()] = None):
#    if not authorization or not authorization.startswith("Bearer "):
#    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
#     token = authorization.removeprefix("Bearer ").strip()
  #  with get_db() as db:
 #       user = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
#    if not user:
#        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

#    return user
class AppError(Exception):
    status_code = 500
    code = "APP_ERROR"
    message = "Something went wrong, please try again later."

class UserAlreadyExistsError(AppError):
    status_code = 409
    code = "USER_EXISTS"
    message = "Email is already registered. Please log in instead."

class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "Could not validate credentials."

class TokenExpiredError(AppError):
    status_code = 401
    code = "TOKEN_EXPIRED"
    message = "Your session has expired. Please log in again."

class InvalidLoginError(AppError):
    status_code = 401
    code = "INVALID_LOGIN"
    message = "Invalid email or password."

class ExternalServiceError(AppError):
    status_code = 503
    code = "EXTERNAL_SERVICE_ERROR"
    message = "This service is temporarily unavailable. Please try again later."

class StoreNotFoundError(AppError):
    status_code = 404
    code = "STORE_NOT_FOUND"
    message = "This store is unavailable. Please refresh and try again."

class FoodUnavailableError(AppError):
    status_code = 404
    code = "FOOD_UNAVAILABLE"
    message = "One or more items in your order are no longer available. Please refresh and try again."

@app.exception_handler(AppError)
def handle_app_error(_, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error":{"code": exc.code,"message":exc.message}}
    )

logger = logging.getLogger(__name__)
@app.exception_handler(Exception)
def exception_handler(_, exc: Exception):
    logger.error("Unhandled exception occurred",exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error":{"code":"INTERNAL_ERROR","message":"Something went wrong, please try again later."}}
    )

@app.exception_handler(RequestValidationError)
def validation_handler(_, exc: RequestValidationError):
    errors = exc.errors()
    error = [error["loc"][-1] for error in errors]
    print(errors)
    message = errors[0]["msg"] if errors and len(errors) < 2 else "Please check your input."
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": message, "details": error}}
    )

@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (payload.name, payload.email.lower(), hash_password(payload.password)),
            )
            user = db.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
    except sqlite3.IntegrityError:
        raise UserAlreadyExistsError()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": str(user["id"])}, access_token_expires)
    user_public = UserPublic(id=user["id"], name=user["name"], email=user["email"])
    return issue_user_response(user_public, Token(access_token=token, token_type="bearer")) #return token_type how to handle?

@app.get("/api/auth/users/me")
def get_users_me(current_user: Annotated[UserPublic, Depends(get_current_user)]):
    return current_user

@app.post("/api/auth/login")
def login(payload: LoginPayload):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
        if not user or not verify_password(user["password_hash"], payload.password):
            raise InvalidLoginError
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": str(user["id"])}, access_token_expires)
    user_public = UserPublic(id=user["id"], name=user["name"], email=user["email"])
    return issue_user_response(user_public, Token(access_token=token, token_type="bearer"))

@app.get("/api/stores")
def list_stores():
    with get_db() as db:
        stores = db.execute("SELECT * FROM stores ORDER BY rating DESC").fetchall()
    return [row_to_dict(store) for store in stores]

@app.get("/api/stores/{store_id}")
def get_store(store_id: int):
    with get_db() as db:
        store = db.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        foods = db.execute("SELECT * FROM foods WHERE store_id = ? ORDER BY popular DESC, id", (store_id,)).fetchall()
    if not store:
        raise StoreNotFoundError
    data = row_to_dict(store)
    data["foods"] = [row_to_dict(food) for food in foods]
    return data

@app.post("/api/orders")
def create_order(payload: OrderPayload, user: UserPublic = Depends(get_current_user)):
    ids = [item.food_id for item in payload.items]
    placeholders = ",".join("?" for _ in ids)
    with get_db() as db:
        foods = db.execute(f"SELECT * FROM foods WHERE id IN ({placeholders})", ids).fetchall()
        food_by_id = {food["id"]: food for food in foods}
        #user experience improvement
        if len(food_by_id) != len(set(ids)):
            raise FoodUnavailableError

        total = sum(food_by_id[item.food_id]["price"] * item.quantity for item in payload.items)
        cursor = db.execute(
            "INSERT INTO orders (user_id, total, status, payment_status) VALUES (?, ?, ?, ?)",
            (user.id, round(total, 2), "created", "pending"),
        )
        order_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO order_items (order_id, food_id, quantity, price) VALUES (?, ?, ?, ?)",
            [
                (order_id, item.food_id, item.quantity, food_by_id[item.food_id]["price"])
                for item in payload.items
            ],
        )
    return {"order_id": order_id, "total": round(total, 2), "status": "created", "payment_status": "pending"}

@app.post("/api/recommendations")
def search_recommendations(payload:SearchInput):
    query = payload.user_input
    with get_db() as db:
        result1 = db.execute("SELECT * FROM stores ORDER BY id ASC").fetchall()
        result2 = db.execute("SELECT * FROM foods ORDER BY store_id ASC").fetchall()

    stores = [row_to_dict(row) for row in result1]
    foods = [row_to_dict(row) for row in result2]

    store_lookup = {}
    for store in stores:
        store['foods'] = []
        store_lookup[store['id']] = store
    for food in foods:
        store_lookup[food['store_id']]['foods'].append(food)
    data = list(store_lookup.values())
    try:
        response = client.chat.completions.parse(
            model="gemini-3.5-flash",
            messages=[
                {"role": "user",
                "content": query + json.dumps(data) + "at most recommend 3 stores and at most 3 types of foods per store"
                }
            ],
            response_format=StoresList,
        )
        result = response.choices[0].message.parsed
        result.stores_recommend = result.stores_recommend[:3]
        for r in result.stores_recommend:
            r.foodlist = r.foodlist[:3]
        return result.stores_recommend
    except:
        raise ExternalServiceError

@app.get("/api/health")
def health():
    return {"ok": True}