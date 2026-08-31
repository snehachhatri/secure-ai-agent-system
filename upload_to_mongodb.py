import pandas as pd
from pymongo import MongoClient
import certifi
import os

uri = "mongodb+srv://kakdeisha809_db_user:bharatmatakijay1234@secure-ai-db.nqflwcc.mongodb.net/?appName=secure-ai-db"

client = MongoClient(
     "mongodb+srv://kakdeisha809_db_user:bharatmatakijay1234@secure-ai-db.nqflwcc.mongodb.net/?appName=secure-ai-db"
,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["secure_ai_gateway"]

files = {
    "patients.csv": "patients",
    "doctors.csv": "doctors",
    "appointments.csv": "appointments",
    "treatments.csv": "treatments",
    "billing.csv": "billing"
}

folder = r".\hospital_rawdata\cleaned"

for file, collection in files.items():
    path = os.path.join(folder, file)

    df = pd.read_csv(path)
    records = df.to_dict("records")

    db[collection].delete_many({})

    if records:
        db[collection].insert_many(records)

    print(f"{collection}: {len(records)} records uploaded")

print("ALL DATA UPLOADED SUCCESSFULLY!")