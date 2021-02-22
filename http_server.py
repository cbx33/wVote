#!/usr/bin/env python3

import datetime
import html as html_lib
import random
import string
import logging
import json

from aiohttp import web, web_request

import bot
import compo

vote_template = open("templates/vote.html", "r").read()
submit_template = open("templates/submit.html", "r").read()
thanks_template = open("templates/thanks.html", "r").read()
admin_template = open("templates/admin.html", "r").read()

favicon = open("static/favicon.ico", "rb").read()

server_domain = "8bitweekly.xyz"
default_ttl = 30

too_big_text = """
File too big! We can only upload to discord files 8MB or less.
You can alternatively upload to SoundCloud or Clyp or something,
and provide us with a link. If you need help, ask us in
#weekly-challenge-discussion.
"""

edit_keys = {
    # "a1b2c3d4":
    # {
    # 	"entryUUID": "cf56f9c3-e81f-43b0-b16b-de2144b54b02",
    # 	"creationTime": datetime.datetime.now(),
    # 	"timeToLive": 200
    # }
}

admin_keys = {
    # "a1b2c3d4":
    # {
    # 	"creationTime": datetime.datetime.now(),
    # 	"timeToLive": 200
    # }
}

vote_keys = {
    #"a1b2c3d4":
    #{
    #  "userID": 336685325231325184,
    #  "userName": "wilm0x42",
    #  "creationTime": datetime.datetime.now(),
    #  "timeToLive": 200
    #}
}

def get_vue_url() -> str:
    if bot.test_mode:
        return "https://cdn.jsdelivr.net/npm/vue@2/dist/vue.js"
    else:
        return "https://cdn.jsdelivr.net/npm/vue@2"

def key_valid(key: str, keystore: dict) -> bool:
    if key not in keystore:
        return False

    now = datetime.datetime.now()
    ttl = datetime.timedelta(minutes=int(keystore[key]["timeToLive"]))

    if now - keystore[key]["creationTime"] < ttl:
        return True
    else:
        del keystore[key]
        return False


def create_key(length: int = 8) -> str:
    key_characters = string.ascii_letters + string.digits
    key = ''.join(random.SystemRandom().choice(key_characters)
                  for _ in range(length))
    return key


def create_edit_key(entry_uuid: str) -> str:
    key = create_key()

    edit_keys[key] = {
        "entryUUID": entry_uuid,
        "creationTime": datetime.datetime.now(),
        "timeToLive": default_ttl
    }

    return key


def create_admin_key() -> str:
    key = create_key()

    admin_keys[key] = {
        "creationTime": datetime.datetime.now(),
        "timeToLive": default_ttl
    }

    return key

def create_vote_key(user_id: int, user_name) -> str:
    key = create_key()
    
    vote_keys[key] = {
        "userID": user_id,
        "userName": user_name,
        "creationTime": datetime.datetime.now(),
        "timeToLive": default_ttl
    }
    
    return key

def get_admin_controls(auth_key: str) -> str:
    this_week = compo.get_week(False)
    next_week = compo.get_week(True)

    html = ""

    def text_field(field: str, label: str, value: str) -> None:
        nonlocal html
        html += "<form action='/admin/edit/%s' " % auth_key
        html += ("onsubmit='setTimeout(function()"
                 "{window.location.reload();},1000);' ")
        html += ("method='post' accept-charset='utf-8' "
                 "enctype='application/x-www-form-urlencoded'>")

        html += "<label for='%s'>%s</label>" % (field, label)
        html += "<input name='%s' type='text' value='%s' />" % (
            field, html_lib.escape(value))
        html += "<input type='submit' value='Submit'/>"
        html += "</form><br>"

    text_field("currentWeekTheme", "Theme/title of current week",
               this_week["theme"])
    text_field("currentWeekDate", "Date of current week", this_week["date"])
    text_field("nextWeekTheme", "Theme/title of next week", next_week["theme"])
    text_field("nextWeekDate", "Date of next week", next_week["date"])

    if compo.get_week(True)["submissionsOpen"]:
        html += "<p>Submissions are currently OPEN</p>"
    else:
        html += "<p>Submissions are currently CLOSED</p>"

    # TODO: Convert this garbage to Vue

    html += "<form action='/admin/edit/%s' " % auth_key
    html += "onsubmit='setTimeout(function(){window.location.reload();},1000);' "
    html += ("method='post' accept-charset='utf-8' "
             "enctype='application/x-www-form-urlencoded'>")
    html += "<label for='submissionsOpen'>Submissions Open</label>"
    html += "<input type='radio' name='submissionsOpen' value='Yes'>"
    html += "<label for='Yes'>Yes</label>"
    html += "<input type='radio' name='submissionsOpen' value='No'>"
    html += "<label for='No'>No</label>"
    html += "<input type='submit' value='Submit'/>"
    html += "</form><br>"
    
    if compo.get_week(False)["votingOpen"]:
        html += "<p>Voting is currently OPEN</p>"
    else:
        html += "<p>Voting is currently CLOSED</p>"

    html += "<form action='/admin/edit/%s' " % auth_key
    html += "onsubmit='setTimeout(function(){window.location.reload();},1000);' "
    html += ("method='post' accept-charset='utf-8' "
             "enctype='application/x-www-form-urlencoded'>")
    html += "<label for='votingOpen'>Voting Open</label>"
    html += "<input type='radio' name='votingOpen' value='Yes'>"
    html += "<label for='Yes'>Yes</label>"
    html += "<input type='radio' name='votingOpen' value='No'>"
    html += "<label for='No'>No</label>"
    html += "<input type='submit' value='Submit'/>"
    html += "</form><br>"

    html += ("<form style='border: 1px solid black;' "
             "action='/admin/edit/%s' " % auth_key)
    html += "onsubmit='setTimeout(function(){window.location.reload();},1000);' "
    html += ("method='post' accept-charset='utf-8' "
             "enctype='application/x-www-form-urlencoded'>")
    html += "<label>Force create an entry</label><br>"
    html += "<label for='newEntryEntrant'>Spoofed entrant name</label>"
    html += "<input type='text' name='newEntryEntrant' value='Wiglaf'><br>"
    html += ("<label for='newEntryDiscordID'>(Optional) "
             "Spoofed entrant discord ID</label>")
    html += "<input type='text' name='newEntryDiscordID' value=''><br>"
    html += ("<label for='newEntryWeek'>Place entry in current week "
             "instead of next week?</label>")
    html += "<input type='checkbox' name='newEntryWeek' value='on'><br>"
    html += "<input type='submit' value='Submit'/>"
    html += "</form><br>"

    html += "<form action='/admin/edit/%s' " % auth_key
    html += "onsubmit='setTimeout(function(){window.location.reload();},1000);' "
    html += ("method='post' accept-charset='utf-8' "
             "enctype='application/x-www-form-urlencoded'>")
    html += ("<label for='rolloutWeek'>Archive current week, "
             "and make next week current</label>")
    html += "<input type='checkbox' name='rolloutWeek' value='on'>"
    html += "<input type='submit' value='Submit'/>"
    html += "</form>"

    return html


async def admin_control_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]

    if key_valid(auth_key, admin_keys):
        this_week = compo.get_week(False)
        next_week = compo.get_week(True)

        data = await request.post()

        def data_param(week, param, field):
            nonlocal data

            if field in data:
                week[param] = data[field]

        data_param(this_week, "theme", "currentWeekTheme")
        data_param(this_week, "date", "currentWeekDate")
        data_param(next_week, "theme", "nextWeekTheme")
        data_param(next_week, "date", "nextWeekDate")

        if "submissionsOpen" in data:
            if data["submissionsOpen"] == "Yes":
                compo.get_week(True)["submissionsOpen"] = True
            if data["submissionsOpen"] == "No":
                compo.get_week(True)["submissionsOpen"] = False
        
        if "votingOpen" in data:
            if data["votingOpen"] == "Yes":
                compo.get_week(False)["votingOpen"] = True
            if data["votingOpen"] == "No":
                compo.get_week(False)["votingOpen"] = False

        if "rolloutWeek" in data:
            if data["rolloutWeek"] == "on":
                compo.move_to_next_week()

        if "newEntryEntrant" in data:
            new_entry_week = True
            if "newEntryWeek" in data:
                new_entry_week = False

            new_entry_discord_id = None
            if "newEntryDiscordID" in data:
                if data["newEntryDiscordID"] != "":
                    try:
                        new_entry_discord_id = int(data["newEntryDiscordID"])
                    except ValueError:
                        new_entry_discord_id = None

            compo.create_blank_entry(data["newEntryEntrant"],
                                     new_entry_discord_id, new_entry_week)
        compo.save_weeks()
        return web.Response(status=204, text="Nice")
    else:
        return web.Response(status=404, text="File not found")


async def vote_handler(request: web_request.Request) -> web.Response:
    html = None

    html = vote_template.replace("[WEEK-DATA]",
                                 compo.get_week_viewer_json(False))

    html = html.replace("[VUE-URL]", get_vue_url())

    return web.Response(text=html, content_type="text/html")


async def week_files_handler(request: web_request.Request) -> web.Response:
    data, content_type = compo.get_entry_file(request.match_info["uuid"],
                                              request.match_info["filename"])

    if not data:
        return web.Response(status=404, text="File not found")

    return web.Response(status=200, body=data, content_type=content_type)


async def favicon_handler(request: web_request.Request) -> web.Response:
    return web.Response(body=favicon)


async def edit_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]

    if not compo.get_week(True)["submissionsOpen"]:
        return web.Response(status=404,
                            text="Submissions are currently closed!")

    if key_valid(auth_key, edit_keys):
        key = edit_keys[auth_key]

        form = compo.get_edit_form_for_entry(key["entryUUID"], auth_key)
        html = submit_template.replace("[ENTRY-FORM]", form)
        html = html.replace("[ENTRANT-NAME]",
                            compo.get_entrant_name(key["entryUUID"]))

        return web.Response(status=200, body=html, content_type="text/html")
    else:
        return web.Response(status=404, text="File not found")

async def admin_preview_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]
    
    if key_valid(auth_key, admin_keys):
        html = None

        html = vote_template.replace("[WEEK-DATA]",
                                     compo.get_week_viewer_json(True))

        html = html.replace("[VUE-URL]", get_vue_url())

        return web.Response(text=html, content_type="text/html")
    else:
        return web.Response(status=404, text="File not found")

async def admin_viewvote_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]
    user_id = request.match_info["userID"]
    
    if key_valid(auth_key, admin_keys):
        html = None

        week = compo.get_week(False)
        
        print("user_id: " + str(user_id))
        
        if not "votes" in week:
            week["votes"] = []
        
        for v in week["votes"]:
            if int(v["userID"]) == int(user_id):
                return web.Response(status=200,
                                    body=json.dumps(v),
                                    content_type="application/json")

        return web.Response(status=404, text="File not found")
    else:
        return web.Response(status=404, text="File not found")
    
async def admin_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]

    if key_valid(auth_key, admin_keys):
        # key = admin_keys[auth_key]
        
        html = admin_template.replace("[VUE-URL]", get_vue_url())
        html = html.replace("[ENTRY-LIST]", compo.get_all_admin_forms(auth_key))
        html = html.replace("[ADMIN-KEY]", auth_key)
        html = html.replace("[ADMIN-CONTROLS]", get_admin_controls(auth_key))
        html = html.replace("[VOTE-DATA]", compo.get_week_votes_json(False))

        return web.Response(status=200, body=html, content_type="text/html")
    else:
        return web.Response(status=404, text="File not found")


# TODO: Break this down to simpler functions
# In particular, doubly-nested while loops contained in doubly-nested
# for loops should probably to be approached differently
async def file_post_handler(request: web_request.Request) -> web.Response:
    auth_key = request.match_info["authKey"]
    uuid = request.match_info["uuid"]

    user_authorized = (key_valid(auth_key, edit_keys)
                       and edit_keys[auth_key]["entryUUID"] == uuid
                       and compo.get_week(True)["submissionsOpen"])

    is_admin = key_valid(auth_key, admin_keys)
    authorized = user_authorized or is_admin
    if not authorized:
        return web.Response(status=403, text="Not happening babe")

    for which_week in [True, False]:
        week = compo.get_week(which_week)

        for entryIndex, entry in enumerate(week["entries"]):
            if entry["uuid"] != uuid:
                continue

            reader = await request.multipart()

            if reader is None:
                return web.Response(status=400, text="Not happening babe")

            while True:
                field = await reader.next()

                if field is None:
                    break

                if field.name == "entryName":
                    entry["entryName"] = \
                        (await field.read(decode=True)).decode("utf-8")
                elif (field.name == "entrantName"
                      and key_valid(auth_key, admin_keys)):
                    entry["entrantName"] = \
                        (await field.read(decode=True)).decode("utf-8")
                elif (field.name == "entryNotes"
                      and key_valid(auth_key, admin_keys)):
                    entry["entryNotes"] = \
                        (await field.read(decode=True)).decode("utf-8")

                elif (field.name == "deleteEntry"
                      and key_valid(auth_key, admin_keys)):
                    week["entries"].remove(entry)
                    compo.save_weeks()
                    return web.Response(status=200,
                                        text="Entry successfully deleted.")

                elif field.name == "mp3Link":
                    url = (await field.read(decode=True)).decode("utf-8")
                    if len(url) > 1:
                        entry["mp3"] = url
                        entry["mp3Format"] = "external"
                        entry["mp3Filename"] = ""

                elif field.name == "mp3" or field.name == "pdf":
                    if field.filename == "":
                        continue

                    size = 0
                    entry[field.name] = None

                    entry[field.name + "Filename"] = field.filename

                    if field.name == "mp3":
                        entry["mp3Format"] = "mp3"

                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > 1000 * 1000 * 8:  # 8MB limit
                            entry[field.name] = None
                            entry[field.name + "Filename"] = None
                            return web.Response(status=413, text=too_big_text)
                        if entry[field.name] is None:
                            entry[field.name] = chunk
                        else:
                            entry[field.name] += chunk
            
            if not is_admin:
                # Move the entry to the end of the list
                week["entries"].append(week["entries"].pop(entryIndex))
            
            compo.save_weeks()

            await bot.submission_message(entry,
                                         key_valid(auth_key, admin_keys))

            if is_admin:
                return web.Response(status=303, headers={"Location": "%s/admin/%s" % (bot.url_prefix(), auth_key)})
            
            thanks = thanks_template.replace("[HEADER]",
                                  "Your entry has been recorded -- Good luck!")
            thanks = thanks.replace("[BODY]",
                "If you have any issues, "
                "let us know in #weekly-challenge-discussion, "
                "or DM one of our friendly moderators.")
            
            return web.Response(status=200,
                                body=thanks,
                                content_type="text/html")

    return web.Response(status=400, text="That entry doesn't seem to exist")

async def submit_vote_handler(request: web_request.Request) -> web.Response:
    vote_input = await request.json()
    
    auth_key = vote_input["voteKey"]
    
    if not key_valid(auth_key, vote_keys):
        return web.Response(status=403, text="Not happening babe")
    
    user_id = vote_keys[auth_key]["userID"]
    user_name = vote_keys[auth_key]["userName"]
    
    week = compo.get_week(False)
    
    if not "votes" in week:
        week["votes"] = []
    
    # If user has submitted a vote already, then remove it, so we can
    # replace it with the new one
    for v in week["votes"]:
        if int(v["userID"]) == int(user_id):
            week["votes"].remove(v)
    
    vote_data = {
        "ratings": vote_input["votes"],
        "userID": user_id,
        "userName": user_name
    }
    
    week["votes"].append(vote_data)
    
    compo.save_weeks()
    
    return web.Response(status=200, text="FRICK yeah")

async def vote_thanks_handler(request: web_request.Request) -> web.Response:
    message = thanks_template.replace("[HEADER]", "Thank you for voting!")
    message = message.replace("[BODY]",
        "Your vote has been recorded.  I will guard it with my life. :)")
    return web.Response(status=200, body=message, content_type="text/html")

# async def debug_handler(request):
#   cmd = request.match_info["command"]

#   if cmd == "save":
#       compo.save_weeks()

#   return web.Response(status=200, text="Nice.")

# for member in bot.client.guilds[0].members:

# async def yeet_handler(request):
#   await bot.client.get_channel(720055562573840384).send("yeet yate yote")
#   return web.Response(text="lmao")

server = web.Application()

server.add_routes([
    web.get("/", vote_handler),
    web.get("/files/{uuid}/{filename}", week_files_handler),
    web.get("/favicon.ico", favicon_handler),
    web.get("/edit/{authKey}", edit_handler),
    web.get("/admin/{authKey}", admin_handler),
    web.get("/admin/preview/{authKey}", admin_preview_handler),
    web.get("/admin/viewvote/{authKey}/{userID}", admin_viewvote_handler),
    web.get("/thanks", vote_thanks_handler),
    web.post("/admin/edit/{authKey}", admin_control_handler),
    web.post("/edit/post/{uuid}/{authKey}", file_post_handler),
    web.post("/submit_vote", submit_vote_handler),
    # web.get("/debug/{command}", debug_handler),
    web.static("/static", "static")
])


async def start_http() -> None:
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8251)
    await site.start()
    logging.info("HTTP: Started server")


if __name__ == "__main__":
    web.run_app(server)
