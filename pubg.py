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

# map_name_to_filter = "Erangel_Main"

# def map_name_filter(map_name):
#     return map_name == map_name_to_filter


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

async def download_telemetry_events_for_match(match):
    telemetry_object_id = match["data"]["relationships"]["assets"]["data"][0]["id"]

    included_objects = match["included"]
    asset_objects = filter(lambda object: object["type"] == "asset", included_objects)

    telemetry_object = next(object for object in asset_objects if object["id"] == telemetry_object_id)

    telemetry_url = telemetry_object["attributes"]["URL"]

    telemetry_events = requests.get(telemetry_url, headers=headers).json()

    print(f"Downloaded telemetry object {telemetry_object_id}")

    return telemetry_events


def get_landing_position_from_telemetry_events(telemetry_events, player_id):
    landing_events = list(filter(lambda object: object["_T"] == "LogParachuteLanding", telemetry_events))

    player_landing_event = next(object for object in landing_events if object["character"]["accountId"] == player_id)

    player_landing_location = player_landing_event["character"]["location"]
    # asset_objects = filter(lambda object: object["id"] == telemetry_object_id, asset_objects)

    # and object["id"] == telemetry_object_id

    return player_landing_location

def get_map_name_from_match(match):
    return match["data"]["attributes"]["mapName"]

def get_number_of_teammates(match, player_id):

    return -1
def get_number_of_enemies_nearby(match, player_id):
    return -1


def get_statistics_for_match(match, telemetry_events, player_id):
    
    placement = get_placement_for_match(match, player_id)
    landing_location = get_landing_position_from_telemetry_events(telemetry_events, player_id)
    map_name = get_map_name_from_match(match)
    landmark = location_to_landmark(landing_location) 
    number_of_teammates = get_number_of_teammates(match, player_id)
    number_of_enemies_nearby = get_number_of_enemies_nearby(match, player_id)

    # return {
    #     "landmark" : landmark,
    #     "placement" : placement, 
    #     "number_of_teammates" : number_of_teammates, 
    #     "map_name" : map_name, 
    #     "landing_location" : landing_location,
    #     "number_of_enemies_nearby" : number_of_enemies_nearby,
    # }

    return (landmark, placement, number_of_teammates, map_name, landing_location, number_of_enemies_nearby)

async def download_match_for_match_id(match_id):
    match = requests.get(f"https://api.pubg.com/shards/steam/matches/{match_id}", headers=headers).json()
    print(f"Downloaded match data for {match_id}")
    return match

# async def get_statistics_for_match_id(match_id, player_id):
    

#     player_statistics = get_statistics_for_match(match, player_id)

#     print(f"Done for {match_id}")

#     return player_statistics
async def download_player_id_from_player_name(player_id):
    player = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player_id}", headers=headers).json()
    player_id = player["data"][0]["id"]
    return player_id

async def download_matches_for_player_id(player_id):
    
    player = requests.get(f"https://api.pubg.com/shards/steam/players/{player_id}", headers=headers).json()

    print(f"Player id: {player_id}")

    matches = player["data"]["relationships"]["matches"]["data"]
    match_ids = list(map(lambda match: match["id"],  matches))

    tasks = []
    for match_id in match_ids:
        task = download_match_for_match_id(match_id)
        tasks.append(task)

    matches = []
    for task in tasks:
        match = await task
        if match is None:
            continue
        matches.append(match)

    return matches

# async def get_statistics_for_player(player_name):

#     player = requests.get(f"https://api.pubg.com/shards/steam/players?filter[playerNames]={player_name}", headers=headers).json()
#     player_id = player["data"][0]["id"]

#     print(f"Player id: {player_id}")

#     matches = player["data"][0]["relationships"]["matches"]["data"]
#     match_ids = list(map(lambda match: match["id"],  matches))


#     tasks = []
#     for match_id in match_ids:
#         task = get_statistics_for_match_id(match_id, player_id)
#         tasks.append(task)


#     player_statistics = []

#     for task in tasks:
#         task_result = await task
#         if task_result is None:
#             continue
#         landing_position, placement = task_result
#         player_statistics.append((landing_position, placement))

#     return player_statistics

def save_to_pickle(object_to_save, fileName):
    with open(fileName, 'wb') as output:
        pickle.dump(object_to_save, output, pickle.HIGHEST_PROTOCOL)

def load_from_pickle(fileName):
    try:
        with open(fileName, 'rb') as input:
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

class DownloadedData:
    player_id = None
    mathces = []

async def download_data_for_player_name(player_name):
    downloaded_data = DownloadedData()

    downloaded_data.player_id = await download_player_id_from_player_name(player_name)

    matches = await download_matches_for_player_id(downloaded_data.player_id)
    
    telemetry_download_tasks = []
    for match in matches:
        telemetry_download_task = download_telemetry_events_for_match(match)
        telemetry_download_tasks.append((match, telemetry_download_task))

    telemetry_data = []
    for match, telemetry_download_task in telemetry_download_tasks:
        telemetry_events = await telemetry_download_task
        telemetry_data.append(telemetry_events)

    downloaded_data.matches = list(zip(matches, telemetry_data))

    # for match in downloaded_data.matches:
    #     telemetry_events = await download_telemetry_events_for_match(match)
    #     downloaded_data.telemetry_data[match] = telemetry_events
    return downloaded_data

async def main():
    cache_file_name = 'downloaded_data_bogi.pkl'
    player_name = "Ugyismegkurlak"
    # player_name = "Battlechicken_"
    redownload_data = False

    downloaded_data = load_from_pickle(cache_file_name)
    


    if downloaded_data is None or redownload_data:
        downloaded_data = await download_data_for_player_name(player_name)
        save_to_pickle(downloaded_data, cache_file_name)

    print("Calculating statistics...")

    # player_id = await download_player_id_from_player_name(player_name)
    player_statistics = []
    for match, telemetry_events in downloaded_data.matches:
        # telemetry_events = downloaded_data.telemetry_data[match]
        statistics_for_singe_match = get_statistics_for_match(match, telemetry_events, downloaded_data.player_id)
        player_statistics.append(statistics_for_singe_match)

    # download_matches_for_player
    # matches = load_from_pickle('matches.pkl')



    # if matches is None or redownload_data:
    #     matches = await download_matches_for_player_id(player_id)
    #     save_to_pickle(matches, 'matches.pkl')

    # player_statistics = []
    # for match in matches:
    #     telemetry_events = await download_telemetry_events_for_match(match)
    #     statistics_for_singe_match = get_statistics_for_match(match, telemetry_events, player_id)
    #     player_statistics.append(statistics_for_singe_match)

    # player_statistics = load_from_pickle('mydata.pkl')


    # if player_statistics is None or redownload_data:
    #     player_statistics = await get_statistics_for_player(player_name)
    #     save_to_pickle(player_statistics, 'mydata.pkl')



    player_statistics_zipped = list(zip(*player_statistics))

    # print(row)
    for row in player_statistics:
        for value in row:
            print(f"{value}, ", end='')
        print("") # uj sor

    # landing_locations = next(player_statistics_zipped)
    # placements = next(player_statistics_zipped)

    # landmarks = player_statistics_zipped[0]
    # placements = player_statistics_zipped[1]

    # landmarks_and_placements = list(zip(landmarks, placements))

    # print(landmarks_and_placements)
    # for landmark, placement in landmarks_and_placements:
    #     print(f"{landmark}, {placement}")
    #     pass

    pass


if __name__ == "__main__":
    # execute only if run as a script
    asyncio.get_event_loop().run_until_complete(main())
    # main()
    # import code
    # code.interact()


