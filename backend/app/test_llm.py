from dotenv import load_dotenv
from openai import OpenAI
import os, json
from db import get_db, row_to_dict
from pydantic import BaseModel

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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


with get_db() as db:
    result1 = db.execute("SELECT * FROM stores ORDER BY id ASC").fetchall()
    result2 = db.execute("SELECT * FROM foods ORDER BY store_id ASC").fetchall()

# need to consider database may not sequence order, don't mix index with business id number/store_id number
stores = [row_to_dict(row) for row in result1]
foods = [row_to_dict(row) for row in result2]
# no need: data = {}
store_lookup = {}  # declare a empty dictionary
for store in stores:
    store['foods'] = []
    store_lookup[store['id']] = store
    # no need: data.append(store_lookup), dic can't use append()

for food in foods:
    store_lookup[food['store_id']]['foods'].append(food)  # foods attribute is array which can use append()

data = list(store_lookup.values())

# response is not accurate, not based on our data
response = client.chat.completions.parse(
    model="gemini-3.5-flash",
    messages=[
        {"role": "user",
         "content": "I wanna eat something spicy" + json.dumps(data) + "at most recommend 3 stores and at most 3 types of foods per store"
         }
    ],
    response_format=StoresList,
)
print('have received response')
result = response.choices[0].message.parsed #为什么到parsed就结束了？
result.stores_recommend = result.stores_recommend[:3]
for r in result.stores_recommend:
    r.foodlist = r.foodlist[:3]
print(result)