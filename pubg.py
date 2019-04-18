import requests
import asyncio
import pickle
import math


def load_api_key():
    with open('api_key.txt', 'r') as file:
        api_key = file.read().replace('\n', '')
        return api_key
    return "missing"

myApiKey = load_api_key()

# myApiKey = ''

headers = {
    'Authorization': myApiKey,
    'Accept': 'application/vnd.api+json',
}
map_name_to_filter = "Erangel_Main"

def get_player_from_participants(participant_objects, player_id_to_find):
    participant_objects = list(participant_objects)
    # print(participant_objects)
    for participant_object in participant_objects:
        player_id = participant_object["attributes"]["stats"]["playerId"]
        # print(player_id)
        if player_id == player_id_to_find:
            return participant_object
    
    return None

def get_participant_for_match(match, player_id_to_find):    
    included_objects = match["included"]
    participant_objects = filter(lambda object: object["type"] == "participant", included_objects)
    player_participant_object = get_player_from_participants(participant_objects, player_id_to_find)
    return player_participant_object

def get_placement_for_match(match, player_id_to_find):
    player_participant_object = get_participant_for_match(match, player_id_to_find)
    return player_participant_object["attributes"]["stats"]["winPlace"]


def get_landing_position_for_match(match, player_id_to_find):
    telemetry_object_id = match["data"]["relationships"]["assets"]["data"][0]["id"]

    included_objects = match["included"]
    asset_objects = filter(lambda object: object["type"] == "asset", included_objects)

    telemetry_object = next(object for object in asset_objects if object["id"] == telemetry_object_id)

    telemetry_url = telemetry_object["attributes"]["URL"]

    telemetry_events = requests.get(telemetry_url, headers=headers).json()

    landing_events = list(filter(lambda object: object["_T"] == "LogParachuteLanding", telemetry_events))

    player_landing_event = next(object for object in landing_events if object["character"]["accountId"] == player_id_to_find)

    player_landing_location = player_landing_event["character"]["location"]
    # asset_objects = filter(lambda object: object["id"] == telemetry_object_id, asset_objects)

    # and object["id"] == telemetry_object_id

    return player_landing_location

def get_map_name_from_match(match):
    return match["data"]["attributes"]["mapName"]

async def get_placement_for_match_id(match_id, player_id):
    match = requests.get(f"https://api.pubg.com/shards/steam/matches/{match_id}", headers=headers).json()
    placement = get_placement_for_match(match, player_id)
    landing_position = get_landing_position_for_match(match, player_id)
    map_name = get_map_name_from_match(match)
    if map_name == map_name_to_filter:
        print(f"Done for {match_id}")
        return (landing_position, placement)

    print(f"Skipping for {match_id} (map: {map_name})")
    return None


async def get_landing_and_placement_data_for_player(player_name):

    player = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player_name}", headers=headers).json()
    player_id = player["data"][0]["id"]

    print(f"Player id: {player_id}")

    matches = player["data"][0]["relationships"]["matches"]["data"]
    match_ids = list(map(lambda match: match["id"],  matches))


    tasks = []
    for match_id in match_ids:
        task = get_placement_for_match_id(match_id, player_id)
        tasks.append(task)


    landing_and_placement = []

    for task in tasks:
        task_result = await task
        if task_result is None:
            continue
        landing_position, placement = task_result
        landing_and_placement.append((landing_position, placement))

    return landing_and_placement

def save_to_pickle(object_to_save):
    with open('mydata.pkl', 'wb') as output:
        pickle.dump(object_to_save, output, pickle.HIGHEST_PROTOCOL)

def load_from_pickle():
    try:
        with open('mydata.pkl', 'rb') as input:
            return pickle.load(input)
    except:
        return None

def distance(v1, v2):
    return math.sqrt(math.pow(v1["x"] - v2["x"], 2) + math.pow(v1["y"] - v2["y"], 2))

def make_vector(x, y):
    vector = {}
    vector["x"] = x
    vector["y"] = y
    return vector

def centimeters_to_meters(location):
    new_location = {}
    new_location["x"] = location["x"] / 100.0
    new_location["y"] = location["y"] / 100.0
    return new_location

def location_to_landmark(location):

    # yasnaya : 5400, 2432 600
    # mylta: 6850, 4600 500
    # shooting: 3416, 1700 500
    # georgopol 2000, 2300 600
    
    location = centimeters_to_meters(location)

    yasnaya = make_vector(5400, 2432)
    shooting = make_vector(3416, 1700)
    mylta = make_vector(6850, 4600)
    georgopol = make_vector(2000, 2300)

    radius = 600

    if distance(location, yasnaya) < radius:
        return "Yasnaya"
    if distance(location, shooting) < radius:
        return "Shooting"
    if distance(location, mylta) < radius:
        return "Mylta"
    if distance(location, georgopol) < radius:
        return "Georgopol"

    return "Other"

async def main():
    player_name = "Battlechicken_"

    landing_and_placement = load_from_pickle()

    redownload_data = False

    if landing_and_placement is None or redownload_data:
        landing_and_placement = await get_landing_and_placement_data_for_player(player_name)
        save_to_pickle(landing_and_placement)
   

    landing_and_placement_zipped = zip(*landing_and_placement)

    landing_locations = next(landing_and_placement_zipped)
    placements = next(landing_and_placement_zipped)

    landmarks = map(location_to_landmark, landing_locations)

    landmarks_and_placements = list(zip(landmarks, placements))

    print(landmarks_and_placements)
    for landmark, placement in landmarks_and_placements:
        print(f"{landmark}, {placement}")
        pass

    pass


if __name__ == "__main__":
    # execute only if run as a script
    asyncio.get_event_loop().run_until_complete(main())
    # main()
    # import code
    # code.interact()


