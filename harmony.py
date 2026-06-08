import asyncio
import os 
import sys
import time
import shutil
import atexit
from lcu_driver import Connector

os.system('title harmony github release')

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

connector = Connector(loop=loop)

target_champion_name = ""
target_champion_id = None
ban_champion_name = ""
ban_champion_id = None

has_picked = False
has_banned = False

champions_map = {}
summoner_id = None

def hide_cursor():
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write('\033[?25h')
    sys.stdout.flush()

atexit.register(show_cursor)

def get_term_width():
    return shutil.get_terminal_size().columns

def typewriter_print(text, delay=0.02):
    if not text:
        print()
        return

    if text.startswith('\n'):
        sys.stdout.write('\n')
        text = text.lstrip('\n')
        
    width = get_term_width()
    padding = max(0, (width - len(text)) // 2)
    
    sys.stdout.write(" " * padding)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write('\n')

def centered_input(prompt, delay=0.03):
    width = get_term_width()
    padding = max(0, (width - len(prompt)) // 2)
    
    sys.stdout.write(" " * padding)
    for char in prompt:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
        
    return input()

def show_loading(duration=1.5):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    width = get_term_width()
    while time.time() < end_time:
        msg = f"{chars[i % len(chars)]} Initializing system modules..."
        sys.stdout.write("\r" + msg.center(width))
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + "System modules loaded.".center(width) + "\n")

@connector.ready
async def connect(connection):
    global summoner_id, champions_map, target_champion_id, ban_champion_id

    typewriter_print("\nLCU Client Connection Established", 0.04)
    print()

    try:
        summoner_res = await connection.request('get', '/lol-summoner/v1/current-summoner')
        summoner_to_json = await summoner_res.json()
        summoner_id = summoner_to_json['summonerId']
        
        champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{summoner_id}/champions-minimal')
        champion_list_to_json = await champion_list.json()
        for champ_data in champion_list_to_json:
            champions_map[champ_data['name'].lower()] = champ_data['id']
            
    except Exception as e:
        typewriter_print(f"Connection data fetch failed: {e}", 0.03)
        return

    if target_champion_name:
        target_champion_id = champions_map.get(target_champion_name.lower())
    if ban_champion_name:
        ban_champion_id = champions_map.get(ban_champion_name.lower())

    typewriter_print(f"Pick: {target_champion_name.capitalize()}", 0.03)
    typewriter_print(f" Ban: {ban_champion_name.capitalize()}", 0.03)
    print()

@connector.ws.register('/lol-matchmaking/v1/ready-check', event_types=('UPDATE',))
async def ready_check_changed(connection, event):
    if event.data['state'] == 'InProgress' and event.data['playerResponse'] == 'None':
        typewriter_print("Match Found! Auto-Accepting...", 0.02)
        try:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept', data={})
        except Exception: pass

@connector.ws.register('/lol-champ-select/v1/session', event_types=('CREATE', 'UPDATE', 'DELETE',))
async def champ_select_changed(connection, event):
    global target_champion_id, ban_champion_id, has_picked, has_banned

    if event.type == 'delete':
        has_picked = False
        has_banned = False
        return

    lobby_session = event.data
    local_player_cell_id = lobby_session['localPlayerCellId']

    for action_list in lobby_session['actions']:
        for action in action_list:
            if action['actorCellId'] == local_player_cell_id and action['isInProgress'] and not action['completed']:
                action_id = action['id']
                action_type = action['type']

                if action_type == 'ban' and ban_champion_id and not has_banned:
                    try:
                        await connection.request('patch', f'/lol-champ-select/v1/session/actions/{action_id}',
                                                 data={"championId": ban_champion_id, "completed": True})
                        has_banned = True
                        typewriter_print(f"Target Banned: {ban_champion_name.capitalize()}", 0.03)
                    except Exception: pass

                elif action_type == 'pick' and target_champion_id and not has_picked:
                    try:
                        await connection.request('patch', f'/lol-champ-select/v1/session/actions/{action_id}',
                                                 data={"championId": target_champion_id, "completed": True})
                        has_picked = True
                        typewriter_print(f"  Target Locked: {target_champion_name.capitalize()}", 0.03)
                    except Exception: pass

@connector.close
async def disconnect(_):
    typewriter_print("\nClient connection lost. Terminating...", 0.05)


if __name__ == '__main__':
    hide_cursor()
    os.system("cls" if os.name == "nt" else "clear")
    
    typewriter_print("\nHarmony", 0.03)
    print()
    
    show_cursor()
    target_champion_name = centered_input("> Champion to pick: ").strip()
    ban_champion_name = centered_input("> Champion to ban:  ").strip()
    hide_cursor()
    
    print()
    show_loading(2.0)
    
    typewriter_print("\nWaiting for League of Legends client...", 0.03)
    
    try:
        connector.start()
    except KeyboardInterrupt:
        typewriter_print("\nUser interrupted process.", 0.02)
