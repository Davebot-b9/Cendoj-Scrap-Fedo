import pymongo

conection = "mongodb://localhost:27017"

client = pymongo.MongoClient(conection)

#obtener la base de datos test
db_test = client.cendojScrap
#collection de base de datos test
collection_test = db_test.consults

db_sentencias_españa = client.sentencias_españa

collection = db_sentencias_españa.sentencias