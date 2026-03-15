import sqlite3


db = sqlite3.connect("test.db")
cursor = db.cursor()

cursor.execute("INSERT INTO testtt (nom, age) VALUES (?, ?)", ("Jzombi", 16))

db.commit()

