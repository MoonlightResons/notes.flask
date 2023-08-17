from peewee import *
import datetime
from flask_login import UserMixin
from playhouse.migrate import PostgresqlMigrator, migrate

db = PostgresqlDatabase(
    'mynotes',
    host = 'localhost',
    port = '5432',
    user = 'zak',
    password = 'qwe123'
)

db.connect()

class BaseModel(Model):
    class Meta:
        database = db


class MyUser(UserMixin, BaseModel):
    username = CharField(max_length=255, null=False, unique=True)
    email = CharField(max_length=255, null=False, unique=True)
    password = CharField(max_length=255, null=False)

    def __repr__(self):
        return self.email
    
class Notes(BaseModel):
    author = ForeignKeyField(MyUser, on_delete='CASCADE',backref='notes')
    notes_name = CharField(max_length=255, null=False)
    content = TextField()
    days_to_delete = CharField(null=True)
    time_to_delete = TimeField(null=True)
    expiration_date = DateTimeField(null=True)
    pinned = BooleanField(default=False)

db.create_tables([MyUser, Notes])

db.close()
