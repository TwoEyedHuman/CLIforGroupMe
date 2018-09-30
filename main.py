import sys, os
import datetime
import curses
import json
import requests
import random

gm_url = "https://api.groupme.com/v3/"  # base url of the GroupMe API

with open("gm_token.txt", "r") as usr_file:  # load the users initialization data
    usr_json = json.loads(usr_file.read())

usr_token = usr_json["token"].encode('ascii', errors='ignore')  # obtain the users access token from json data


def pull_messages(token, count, usr_grp, screen_width, msg_tp="group"):  # pull the latest messages from a group chat or DM
    if msg_tp == "group":
        r_url = gm_url + "groups/" + str(usr_grp) + "/messages?token=" + token + "&limit=" + str(count)
        r = requests.get(r_url)
        r_json = json.loads(r.text)
        try:
            message_list = r_json['response']['messages']
        except:
            message_list = []
    else:
        r_url = gm_url + "direct_messages?other_user_id=" + str(usr_grp) + "&token=" + token + "&limit=" + str(count)
        r = requests.get(r_url)
        r_json = json.loads(r.text)
        try:
            message_list = r_json['response']['direct_messages']
        except:
            message_list = []

    msg_arr = ["" for x in range(count)]  # initial array to hold the mesages and message data
    for msg_i, msg in enumerate(reversed(message_list), start=0):
        if msg['text'] is None:  # No text means the user posted an image
            ret_msg = msg['name'] + " posted an image."
        elif len(msg['favorited_by']) > 0:  # Check if the are any likes on the message
            ret_msg = msg['name'] + ": " + msg['text'].encode('ascii', errors='ignore')
            num_spaces = screen_width - len(ret_msg) - 6
            ret_msg = ret_msg + (" " * num_spaces) + "<3 x " + str(len(msg['favorited_by']))
        else:
             ret_msg = msg['name'] + ": " + msg['text'].encode('ascii', errors='ignore')
        msg_arr[msg_i] = ret_msg  # add message to the message list

    return msg_arr


def get_active_groups(token):  # pulls the list of groups that the user is a part of
    act_grps = []
    r_url = gm_url + "groups?token=" + token
    r = requests.get(r_url)
    r_json = json.loads(r.text)
    for grp in r_json['response']:  # iterate through groups, and build list containing the ID, name, and number of members
        act_grps.append([grp['group_id'], grp['name'], len(grp['members'])])

    r_url = gm_url + "chats?token=" + token
    r = requests.get(r_url)
    r_json = json.loads(r.text)
    for chat in r_json['response']:
        act_grps.append([chat['other_user']['id'], chat['other_user']['name'], 1])

    return act_grps


def print_groups(grps):  # build an array that displays each groups information
    grp_disp = []
    for grp_i, grp in enumerate(grps):  # iterate over each group, building its display
        if grp[2] > 1:
            grp_disp.append(grp[1].encode('ascii', errors='ignore') + " (" + str(grp[2]).encode('ascii', errors='ignore') + " members)")  # grp[1] is the group name and grp[2] is the group size
        elif grp[2] == 1:
             grp_disp.append(grp[1].encode('ascii', errors='ignore'))  # grp[1] is the group name and grp[2] is the group size
        else:
            raise ValueError("No members in chat.")
    return grp_disp

def send_message(token, msg_txt, usr_grp_id, chat_type = "group"):  # send a message to the currently active chat
    if chat_type == "group":  # chat type is a group
        msg_url = "https://api.groupme.com/v3/groups/" + usr_grp_id + "/messages?token=" + token
        post_data = {
        "message": {
            "source_guid": str(random.randint(12345,12345678)),
            "text": msg_txt
            }
        }

    elif chat_type == "dm":  # chat type is a direct message
        msg_url = gm_url + "direct_messages?token=" + token
        post_data = {
        "direct_message": {
            "source_guid": str(random.randint(12345,12345678)),  # a different guid is needed in any given minute
            "recipient_id": usr_grp_id,
            "text": msg_txt
            }
        }
    else:
        raise ValueError("Incorrect chat type in function send_message.")

    requests.post(msg_url, json=post_data)  # post the json data to server

def gm(stdscr):
    time_interval = 15  # represents the rate at which new messages are pulled
    scr_h, scr_w = stdscr.getmaxyx()  # screen dimensions
    group_id = usr_json["group"]  # id of the default group
    cur_chat_type = "group"
    disp_arr = pull_messages(usr_token, scr_h-1, group_id, scr_w, cur_chat_type)  # pull initial set of messages
    cursor = [2, scr_h-1]  # initial position of cursor
    usr_in = ""

    stdscr.clear()  # remove contents from screen
    stdscr.refresh()  # print current information to screen
    is_exit = 1  # 1 represent conintue, 0 represents exit
    last_update = datetime.datetime.now()
    curses.halfdelay(5)  # if no user input, refresh the display every 5 seconds

    while (is_exit != 0):  # iterate through time, until the user wants to quit
#        stdscr.refresh() 

        cur_time = datetime.datetime.now()
        if (cur_time - last_update).total_seconds() > time_interval:  # check if enough time has passed to update the message list
            last_update = cur_time
            stdscr.clear()
            disp_arr = pull_messages(usr_token, scr_h-1, group_id, scr_w, cur_chat_type)

        for i, msg in enumerate(disp_arr):  # iterate through the display array and print to screen
            stdscr.addstr(i,0,msg.replace("\n","")[0:scr_w].encode('ascii'))
    
        stdscr.addstr(scr_h-1, 0, ">")  # user input indicator
        stdscr.addstr(scr_h-1, 2, usr_in)  # print the partially typed user input to the screen
        usr_in_char = stdscr.getch(cursor[1],cursor[0])  # capture the character that the user typed
        if usr_in_char == 10:  # if the user pressed 'enter'
            if usr_in[0:1] == "\\" or usr_in[0:1] == "/":  # backslash represents interactive mode
                if usr_in[1:] == "quit" or usr_in[1:] == "exit":  # check if the user wants to exit the program
                    is_exit = 0
                elif usr_in[1:] == "refresh":  # check if the user wants to load the messages prematurely
                    disp_arr = pull_messages(usr_token, scr_h-1, group_id, scr_w, cur_chat_type)
                elif usr_in[1:4] == "set":  # let the user define some global variables
                    if usr_in[5:16] == "refresh rate":  # rate at which new messages are pulled
                        time_interval = int(usr_in[18:])
                    elif usr_in[5:10] == "group":  # change the group they are in based on ID
                        group_id = int(usr_in[11:])
                elif usr_in[1:] == "switch":  # let the user interactively choose which group they want to switch to
                    menu_done = False
                    my_grps = get_active_groups(usr_token)
                    disp_arr = print_groups(my_grps)
                    sel_cursor = [0,0]
                    while not menu_done:  # iterate through each keypress
                        sel_char = stdscr.getch()
                        if sel_char == 10:  # if user pressed 'enter'
                            group_id = my_grps[sel_cursor[1]][0]  # change group ID to the one currently highlighted
                            menu_done = True
                            if my_grps[sel_cursor[1]][2] == 1:  # check if the chat is a direct message
                                cur_chat_type = "dm"
                            elif my_grps[sel_cursor[1]][2] > 1:
                                cur_chat_type = "group"
                            disp_arr = pull_messages(usr_token, scr_h-1, group_id, scr_w, cur_chat_type)
                        elif sel_char == curses.KEY_UP:
                            sel_cursor[1] = max(0, sel_cursor[1] - 1)  # move the cursor up one position
                        elif sel_char == curses.KEY_DOWN:
                            sel_cursor[1] = min(min(scr_h-1, sel_cursor[1] + 1), len(my_grps))  # move the cursor down one position
                        else:
                            stdscr.clear()
                            for i, grp in enumerate(disp_arr):
                                stdscr.addstr(i, 0, grp.encode('ascii'))

                        stdscr.move(sel_cursor[1], sel_cursor[0])
                        stdscr.refresh()
                        
            else:
                send_message(usr_token, usr_in, str(group_id), cur_chat_type)
            usr_in = ""
            cursor = [2,scr_h-1]
            stdscr.clear()

        else:
            if usr_in_char >= 32 and usr_in_char <=126 and len(usr_in) < scr_w-3:  # if user typed in a displayable character
                stdscr.clear()
                usr_in = usr_in + chr(usr_in_char)
                cursor[0] = min(cursor[0]+1,scr_w-1)
            elif usr_in_char == 8 or usr_in_char == 127:  # if user typed in backspace
                stdscr.clear()
                usr_in = usr_in[:-1]
                cursor[0] = max(cursor[0]-1,2)
        

def main():
    curses.wrapper(gm)

if __name__ == "__main__":
    main()
