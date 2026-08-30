from pymongo import MongoClient

uri = "mongodb+srv://kakdeisha809_db_user:<db_password>@secure-ai-db.nqflwcc.mongodb.net/"

client = MongoClient(uri)

print(client.admin.command("ping"))
