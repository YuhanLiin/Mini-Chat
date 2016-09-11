#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import hashlib
import hmac
import cgi
import json
import re
import time
from google.appengine.api import channel
import logging

from model import Message, readMessage, writeMessage, chatLogJson, User

#Regex for checking for valid names
NAMEREG = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
#Secret for making cookies with HMAC
COOKIESECRET = "shhhh"

#Specifies template directory
templateDir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(templateDir), autoescape=True)

########################################################################################3

#Returns hmac sha256 hash of a string. Helper function
def hashCookie(text):
    return hmac.new(COOKIESECRET, text, hashlib.sha256).hexdigest()

#Base class for all handler classes
class Handler(webapp2.RequestHandler):
    #Writes response
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    #Returns string of a rendered template given template filename and parameters
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    #Writes rendered template to client
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    #Sends cookie of a username and its hash, separated by |, to browser for validation after user picks name.
    def sendCookie(self, sender, path='/'):
        self.response.headers.add_header('Set-Cookie', 'username=%s|%s; Path=%s' % (str(sender), hashCookie(sender), path))

    #Read a cookie of a username and returns the name if cookie is valid.
    def getCookie(self):
        cookie = self.request.cookies.get('username')
        #Return none if cookie doesnt exist
        if not cookie:
            return None
        cookie = cookie.split('|')
        #Return none of cookie cannot be parsed correctly or if the hash does not match
        if len(cookie) != 2 or hashCookie(cookie[0]) != cookie[1]:
            return None
        return cookie[0]

    #Upon any request the handler reads the cookie on the client to get and store the name of the sender joining the chat
    def initialize(self, *a, **kw):
        super(Handler, self).initialize(*a, **kw)
        sender = self.getCookie()
        self.sender = sender



#Handler for the page where usernames are picked "/name"
class NameHandler(Handler):
    #Check a new username for potential errors. Also checks the stored usernames for repeats and clears expired names.
    #Returns True if name passes, False otherwise
    def checkName(self, name):
        #Error when name does not match proper format
        if not NAMEREG.match(name):
            self.render('name.html', error='Invalid username.')
        #Otherwise check for if the name has been taken
        elif User.exists(name):
            self.render('name.html', error='Username already in use.')
        else:
            return True
        return False

    def get(self):
        error=self.request.get("error")
        self.render("name.html", error=error)

    #Runs upon name submission
    def post(self):
        sender = self.request.get('name')
        #Valid users are given a cookie and sent to the main site
        if self.checkName(sender):
            self.sendCookie(sender)
            self.redirect('/')

#Main page where chat is held
class ChatHandler(Handler):
    #Add the current user to a new channel and set its expiry time to 2 hours after. Return channel token
    def addUser(self):
        token = channel.create_channel(self.sender)
        return token

    #Updates all connected channels with message and delete old ones
    def updateAllUsers(self, message):
        users = User.getAll()
        for user in users:
            #For every user update channel with new message.
            channel.send_message(user.name, message)

    #Create a channel for each page load so user can connect and receive instant updates
    def get(self):
        #If name is invalid or absent redirect to name-choosing page
        if not self.sender:
            self.redirect('/name')
            return
        #If name has been taken redirect to name-choosing page
        if User.exists(self.sender):
            self.redirect('/name?error=Username+already+in+use.')
            return
        token = self.addUser()
        #Send token and the last 100 messages to the client javascript
        chatlog = chatLogJson(Message.count())
        self.render('chat.html', token=token, chatlog=chatlog, name=self.sender)

    #Runs whenever a client sends a message.
    def post(self):
        #If cookie name is invalid redirect to name-choosing page
        if not self.sender:
            self.redirect('/name')
            return
        #If there's a mismatch between cookie name and page username then redirect to name page.
        name = self.request.get("name")
        if name != self.sender:
            self.response.headers["content-type"] = "text/plaintext"
            self.write('/name')
            return
        #If message is empty then dont take request
        message = cgi.escape(self.request.get("message"))
        if not message:
            return
        #Writes new message to db and then read it as json
        obj = writeMessage(self.sender, message)
        json = obj.toJson()
        #Send message to every connected client
        self.updateAllUsers(json)

class ConnectHandler(Handler):
    def post(self):
        name = self.request.get("from")
        if name:
            User.add(name)
            logging.warning("Add: "+name)

class DisconnectHandler(Handler):
    def post(self):
        name = self.request.get("from")
        if name:
            User.remove(name)
            logging.warning("Remove: "+name)

app = webapp2.WSGIApplication([
    ('/', ChatHandler),
    ('/name', NameHandler),
    ('/_ah/channel/connected/', ConnectHandler),
    ('/_ah/channel/disconnected/', DisconnectHandler)
], debug=True)
