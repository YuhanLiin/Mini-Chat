import json
import logging
from google.appengine.ext import ndb
from google.appengine.api import memcache

#Messages are stored individually in memcache with their ID as keys.

#Model for chat messages. Fields for the name of the sender, the message contents, and the date sent.
#IDs represent the order in which the messages were created and go from 1 onwards.
class Message(ndb.Model):
    sender = ndb.StringProperty(required=True)
    content = ndb.TextProperty(required=True)
    date = ndb.DateTimeProperty(required=True, auto_now_add=True)

    #Counts the # of total messages in db.
    @staticmethod
    def count():
        return len(ndb.gql("select * from Message").fetch())

    #Turns message into dictionary sent as json to the client
    def toDict(self):
        return {'sender': str(self.sender), 'date': self.date.strftime('%b %d, %Y at %H:%M:%S'), 'content': str(self.content)}

    def toJson(self):
        return json.dumps(self.toDict())

    #Generates constant parent key for all messages to sync operations
    @staticmethod
    def parentKey():
        return ndb.Key("chat", "default")

#Get a message by its id from cache or db. Cache it if it's not cached.
def readMessage(num):
    num = str(num)
    message = memcache.get(num)
    if not message:
        logging.critical(num)
        message = ndb.gql("SELECT * FROM Message WHERE __key__ = KEY('chat', 'default', 'Message', :id)", id=num).get()
        memcache.set(num, message)
    return message

#Write a message to both db and cache using the appropriate ID. Return the message count.
def writeMessage(sender, content):
    count = Message.count()
    new = Message(sender=sender, content=content, id=str(count+1), parent=Message.parentKey())
    new.put()
    memcache.set(str(count+1), new)
    return new

#Return all messages from id start to id end as listed json. Default range returns latest 100 messages.
def chatLogJson(end):
    li = []
    logging.critical(end)
    logging.critical(Message.count())
    #Cannot start from below 1.
    start = max(end-100, 1)
    for num in xrange(start, end+1):
        li.append(readMessage(num).toDict())
    j = json.dumps(li)
    return j

###################################################################################################3
####################### Old user model for main.py. Deprecated for new User class #####################

# #DB model for a list of all users and their token expiry times using dictionary property.
# #Only one instance allowed in db.
# class UserMap(ndb.Model):
#     users = ndb.JsonProperty(required=True)

#     #Retrieves expiry time for one user
#     def get(self, user):
#         if user not in self.users:
#             return None
#         return self.users[user]

#     #Extract entire dictionary to minimize db hits
#     def getAll(self):
#         return self.users

#     #Adds one user to map
#     def set(self, user, time):
#         self.users[user] = time
#         self.put()

#     #Overwrite entire dictionary to minimize db hits
#     def setAll(self, dic):
#         self.users = dic
#         self.put()

#     #Extracts the single UserMap from db
#     @staticmethod
#     def extract():
#         users = ndb.gql("select * from UserMap limit 1").get()
#         if not users:
#             users = UserMap(users={}, parent=Message.parentKey())
#             users.put()
#         return users

##################################################################################################
class User(ndb.Model):
    name = ndb.StringProperty(required=True)

    @staticmethod
    def parentKey():
        return ndb.Key("Users", "default")

    @staticmethod
    def add(name):
        sameName = ndb.gql('select * from User where name=:name limit 1', name=name).get()
        if sameName:
            return False
        else:
            user = User(name=name, parent=User.parentKey())
            user.put()
            return True

    @staticmethod
    def remove(name):
        user = ndb.gql('select * from User where name=:name limit 1', name=name).get()
        if user:
            user.key.delete()

    @staticmethod
    def getAll():
        users = ndb.gql('select * from User').fetch()
        return users

    @staticmethod
    def exists(name):
        user = ndb.gql('select * from User where name=:name limit 1', name=name).get()
        if user:
            return True
        return False



