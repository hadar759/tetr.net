import copy
import json
from typing import Dict

from requests import post, get


class ServerCommunicator:
    def __init__(self):
        self.SERVER_DOMAIN = f"https://tetr-net.herokuapp.com"

    @staticmethod
    def bool_to_string(condition: bool):
        return str(condition).lower()

    def get_invite_room(self, username):
        return get(
            f"{self.SERVER_DOMAIN}/users/invite-room?username={username}"
        ).text.replace('"', "")

    def get_server_by_ip(self, ip):
        return json.loads(get(f"{self.SERVER_DOMAIN}/users/server/ip?ip={ip}").content)

    def get_players_in_room(self, room):
        return int(
            get(
                f"{self.SERVER_DOMAIN}/users/rooms/players?room_name={room['name']}&outer_ip={room['outer_ip']}"
            ).text
        )

    def update_controls(self, username: str, controls: Dict):
        controls_with_username = copy.deepcopy(controls)
        controls_with_username["username"] = username
        post(
            f"{self.SERVER_DOMAIN}/users/controls",
            data=json.dumps(controls_with_username),
        )

    def delete_server_by_ip(self, outer_ip: str, inner_ip: str):
        post(
            f"{self.SERVER_DOMAIN}/users/server/del-by-ip?outer_ip={outer_ip}&inner_ip={inner_ip}"
        )

    def update_music(self, username: str, music: bool):
        post(f"{self.SERVER_DOMAIN}/users/music?username={username}&music={music}")

    def update_settings(
        self, username: str, das: int, arr: int, skin: int, ghost: bool, fade: bool
    ):
        post(
            f"{self.SERVER_DOMAIN}/users/settings?username={username}&das={das}&arr={arr}&skin={skin}&ghost={ghost}&fade={fade}"
        )

    def is_password_new(self, user_email, password):
        return (
            get(
                f"{self.SERVER_DOMAIN}/pass/new?user_email={user_email}&password={password}"
            ).text
            == "true"
        )

    def update_password(self, user_email, password):
        post(
            f"{self.SERVER_DOMAIN}/pass/update?user_email={user_email}&password={password}"
        )

    def check_code(self, user_email, code):
        return (
            get(
                f"{self.SERVER_DOMAIN}/pass/check?user_email={user_email}&code={code}"
            ).text
            == "true"
        )

    def user_create_code(self, user_email):
        post(f"{self.SERVER_DOMAIN}/users/create/code?user_email={user_email}")

    def reset_password(self, user_email):
        post(f"{self.SERVER_DOMAIN}/pass/reset?user_email={user_email}")

    def accept_friend_request(self, sender, recipient):
        post(
            f"{self.SERVER_DOMAIN}/users/friends/accept?sender={sender}&recipient={recipient}"
        )

    def send_friend_request(self, sender, recipient):
        post(
            f"{self.SERVER_DOMAIN}/users/friends/send?sender={sender}&recipient={recipient}"
        )

    def remove_friend(self, sender, recipient):
        post(
            f"{self.SERVER_DOMAIN}/users/friends/remove?sender={sender}&recipient={recipient}"
        )

    def get_user_profile(self, username):
        return json.loads(
            get(f"{self.SERVER_DOMAIN}/users/profile?username={username}").content
        )

    def get_apm_leaderboard(self):
        return json.loads(get(f"{self.SERVER_DOMAIN}/users/apms").content)

    def get_marathon_leaderboard(self):
        return json.loads(get(f"{self.SERVER_DOMAIN}/users/marathons").content)

    def get_sprint_leaderboard(self, line_num):
        return json.loads(
            get(f"{self.SERVER_DOMAIN}/users/sprints?line_num={line_num}").content
        )

    def remove_room(self, room_name):
        post(f"{self.SERVER_DOMAIN}/users/rooms/delete?room_name={room_name}")

    def update_player_num(self, outer_ip, inner_ip, player_num):
        post(
            f"{self.SERVER_DOMAIN}/users/rooms/player-num?outer_ip={outer_ip}&inner_ip={inner_ip}&player_num={player_num}"
        )

    def create_room(self, room: Dict):
        """Adds a new room to the database"""
        post(f"{self.SERVER_DOMAIN}/users/rooms", data=json.dumps(room))

    def add_game(self, username: str, win: bool):
        """Updates the user's stats after a game is played"""
        post(f"{self.SERVER_DOMAIN}/users/games?username={username}&win={win}")

    def update_sprint(self, username: str, time: float, line_num: int):
        """Updates the user top sprint time to the given time, and returns true if it's a new fastest time"""
        return (
            post(
                f"{self.SERVER_DOMAIN}/users/sprint?username={username}&cur_time={time}&line_num={line_num}"
            ).text
            == "true"
        )

    def update_marathon(self, username: str, score: int):
        """Updates the top marathon score, and returns true if it's a new high score"""
        return (
            post(
                f"{self.SERVER_DOMAIN}/users/marathon?username={username}&score={score}"
            ).text
            == "true"
        )

    def update_apm(self, username: str, attacks: int, time: float):
        """Updates the apm for the player"""
        # Add the game to the players list of games, and make the apm the attacks / the time in mins
        apm = (attacks / time) * 60
        post(f"{self.SERVER_DOMAIN}/users/apm?username={username}&apm={apm}")

    def get_rooms(self):
        """Returns the list containing all active rooms"""
        rooms = get(f"{self.SERVER_DOMAIN}/users/rooms")
        return json.loads(rooms.content)

    def on_connection(self, username: str, ip: str):
        post(f"{self.SERVER_DOMAIN}/users/connection?username={username}&ip={ip}")

    def get_invite_ip(self, username: str) -> str:
        return get(
            f"{self.SERVER_DOMAIN}/users/invite-ip?username={username}"
        ).text.replace('"', "")

    def dismiss_invite(self, invitee: str):
        post(
            f"{self.SERVER_DOMAIN}/users/invites?inviter={''}&invitee={invitee}&invite_ip={''}&invite_room={''}"
        )

    def get_invite(self, username: str) -> str:
        """Return the current invite for the user"""
        return get(
            f"{self.SERVER_DOMAIN}/users/invites?username={username}"
        ).text.replace('"', "")

    def invite_user(self, inviter: str, invitee: str, invite_ip: str, room_name: str):
        """Invites a given player to a given server ip"""
        post(
            f"{self.SERVER_DOMAIN}/users/invites?inviter={inviter}&invitee={invitee}&invite_ip={invite_ip}&room_name={room_name}"
        )

    def update_online(self, username: str, online: bool):
        """Changes the online state of a given player"""
        post(
            f"{self.SERVER_DOMAIN}/users/online?username={username}&online={self.bool_to_string(online)}"
        )

    def is_online(self, foe_name: str) -> bool:
        """Returns whether a given player is online"""
        return (
            get(f"{self.SERVER_DOMAIN}/users/online?username={foe_name}").text == "true"
        )

    def create_user(self, db_post: dict):
        """Adds a new user to the database"""
        post(f"{self.SERVER_DOMAIN}/users", data=json.dumps(db_post))

    def estimated_document_count(self) -> int:
        """Returns num of queries in the database. Mainly used for testing"""
        return int(get(f"{self.SERVER_DOMAIN}/users/len").text)

    def user_identifier_exists(self, user_identifier: str) -> bool:
        """Returns whether a user with a given user identifier exists in the database"""
        return (
            get(
                f"{self.SERVER_DOMAIN}/users/find?user_identifier={user_identifier}"
            ).text
            == "true"
        )

    def username_exists(self, username: str) -> bool:
        """Returns whether a user with a given username exists in the database"""
        return (
            get(f"{self.SERVER_DOMAIN}/users/find?username={username}").text == "true"
        )

    def email_exists(self, email: str) -> bool:
        """Returns whether a user with a given email exists in the database"""
        return get(f"{self.SERVER_DOMAIN}/users/find?email={email}").text == "true"

    def get_user(self, user_identifier: str, password: str) -> dict:
        """Returns a dict of a user in the database with the given user_identifier and password"""
        resp = get(
            f"{self.SERVER_DOMAIN}/users?user_identifier={user_identifier}&password={password}"
        )
        # Load the user's information onto a tuple
        return json.loads(resp.text)
