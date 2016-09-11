//Turn a single message object from server into html representing a message.
function processMessage(message){
    var mySender = "", myContent = "";
    console.log(name);
    console.log(message.sender);
    if (name === message.sender){
        mySender = " my-sender";
        myContent = " my-content";
    }
    var ans = '<span class="message-date">' + message.date + ' </span><span class="message-sender'+ mySender +'">'
                    + message.sender + ': </span><span class="message-content' + myContent + '">'+ message.content
                    + '</span><br>';
    return ans;
}

//Turn a chatlog object from server into html by concatenating all message html.
function processChat(chatlog){
    var chat = ""
    for (i in chatlog){
        chat += processMessage(chatlog[i]);
    }
    return chat;
}

function scrollBottom(){
    $("#chatbox").scrollTop($("#chatbox").prop("scrollHeight"));
}

//When a message is received from server, parse json message data and append it to the chat window
function onmessage(message){
    var json = JSON.parse(message.data);
    $("#chatbox").append(processMessage(json));
    scrollBottom();
}

//When socket closes reload the page for a new token and socket
function onclose(){
    location.reload();
}

function submitMessage(event){
    event.preventDefault();
    if ($("#messagebox").val() === ""){
        return;
    }
    var params = $("#chatform").serialize()+"&name="+name;
    $.post(window.location.pathname, params,
            function(data){
                if (data){
                    window.location.pathname = data;
                }
            });
    $("#messagebox").val("");
    scrollBottom();
}
//////////////////////////////////////////////////////////////////////////////////////////////////

$("#chatform").submit(submitMessage);
//When the page is loaded write the last 100 messages to the chat window
$("#chatbox").html(processChat(chatlog));
scrollBottom();
//Initializes socket with handlers
var channel = new goog.appengine.Channel(token);
var handler = { 'onopen': function() {},
                'onmessage': onmessage,
                'onerror': function() {},
                'onclose': onclose};
var socket = channel.open(handler);