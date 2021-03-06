from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import pickle
import socket
import threading
import time
from typing import Optional, Dict

import pygame

from database.server_communicator import ServerCommunicator
from menus.friend_screen import FriendsScreen
from menus.leaderboard_screen import LeaderboardScreen
from menus.menu_screen import MenuScreen
from menus.settings_screen import SettingsScreen
from menus.waiting_room import WaitingRoom
from tetris.colors import Colors
from menus.room_screen import RoomsScreen
from tetris.tetris_game import TetrisGame
from menus.user_profile_screen import UserProfile


class MainMenu(MenuScreen):
    """The starting screen of the game"""

    GAME_PORT = 44444
    BUTTON_PRESS = pygame.MOUSEBUTTONDOWN
    BACKGROUND_MUSIC = {"theme": pygame.mixer.Sound("sounds/01. Main Menu.mp3")}
    for sound in BACKGROUND_MUSIC.values():
        sound.set_volume(0.05)

    def __init__(
        self,
        user: Dict,
        cache,
        server_communicator: ServerCommunicator,
        width: int,
        height: int,
        refresh_rate: int = 60,
        background_path: Optional[str] = None,
        skin: int = 1,
    ):
        super().__init__(
            width, height, server_communicator, refresh_rate, background_path
        )
        self.user = user
        self.skin = skin
        self.text_cursor_ticks = pygame.time.get_ticks()
        self.socket = socket.socket()
        self.cache = cache

    def run(self):
        """Main loop of the main menu"""
        while True:
            # Play background music
            self.BACKGROUND_MUSIC["theme"].play(1000, fade_ms=5000)
            # Music is turned off - just pause so we can unpause if the user toggles
            if not self.user["music"]:
                pygame.mixer.pause()
            # Display the menu
            self.create_menu()
            # For invite checking
            old_time = round(time.time())

            self.on_menu_start()

            while self.running:
                self.run_once()

                # Display invites
                cur_time = round(time.time())
                if cur_time % 10 == 0 and cur_time != old_time:
                    old_time = cur_time
                    threading.Thread(target=self.check_invite, daemon=True).start()
                pygame.display.flip()

    def keep_cache_updated(self):
        while self.running:
            time.sleep(10)
            new_cache = self.cache_stats(self.user["username"])
            # Update the relevant cache parts
            for key in new_cache:
                self.cache[key] = new_cache[key]

    def on_menu_start(self):
        """Threads to be started when this screen is opened"""
        self.running = True
        threading.Thread(target=self.update_mouse_pos, daemon=True).start()
        threading.Thread(target=self.keep_cache_updated, daemon=True).start()

    def check_invite(self):
        """Check whether the user was invited"""
        invite = self.server_communicator.get_invite(self.user["username"]).replace(
            '"', ""
        )
        if invite:
            self.display_invite(invite)

    def display_invite(self, inviter_name):
        """screen_corner_x = 1500
        screen_corner_y = 600
        button_height = 300
        button_width = 200
        self.create_button(
            (screen_corner_x - button_width, screen_corner_y - button_height),
            button_width,
            button_height,
            Colors.BLACK_BUTTON,
            inviter_name,
            func=self.accept_invite,
        )"""

        button_width = 600
        button_height = 400
        self.create_button(
            (
                self.width // 2 - button_width // 2,
                self.height // 2 - button_height // 2,
            ),
            button_width,
            button_height,
            Colors.BLACK_BUTTON,
            f"{inviter_name}\n",
        )

        self.create_button(
            (
                self.width // 2 - button_width // 2,
                self.height // 2 - button_height // 2 - 135,
            ),
            button_width,
            button_height,
            Colors.BLACK_BUTTON,
            f"invitation!",
            text_only=True,
            text_color=Colors.GREEN,
        )

        action_width = 200
        action_height = 100
        self.create_button(
            (
                self.width // 2 - action_width // 2 - 150,
                self.height // 2 - button_height // 2 + 250,
            ),
            action_width,
            action_height,
            Colors.BLACK_BUTTON,
            "Accept",
            text_size=30,
            text_color=Colors.GREEN,
            func=self.accept_invite,
        )

        self.create_button(
            (
                self.width // 2 - action_width // 2 + 150,
                self.height // 2 - button_height // 2 + 250,
            ),
            action_width,
            action_height,
            Colors.BLACK_BUTTON,
            "Reject",
            text_size=30,
            text_color=Colors.RED,
            func=self.dismiss_invite,
        )

    def accept_invite(self):
        # Make it inner and outer
        invite_ip = self.server_communicator.get_invite_ip(self.user["username"])
        invite_room = self.server_communicator.get_invite_room(self.user["username"])
        inviter_name = self.server_communicator.get_invite(self.user["username"])
        threading.Thread(
            target=self.server_communicator.invite_user,
            args=(
                "",
                self.user["username"],
                "",
                "",
            ),
        ).start()

        room = {"name": invite_room, "ip": invite_ip}
        self.connect_to_room(room)

        self.remove_button(inviter_name)
        self.update_screen()

    def connect_to_room(self, room: Dict):
        sock = socket.socket()
        sock.connect((room["ip"], 44444))
        # Start the main menu
        waiting_room = WaitingRoom(
            self.cache["user"],
            False,
            room["name"],
            self.cache,
            sock,
            self.server_communicator,
            self.width,
            self.height,
            75,
            "tetris/tetris-resources/tetris_background.jpg",
        )
        self.running = False
        waiting_room.run()
        self.cache = waiting_room.cache
        self.on_menu_start()

    def dismiss_invite(self):
        """Dismisses an invite from a player"""
        inviter_name = self.server_communicator.get_invite(self.user["username"])
        invite_ip = self.server_communicator.get_invite_ip(self.user["username"])
        self.socket.connect((invite_ip, 44444))
        # Notify the server of declination
        self.socket.send(f"Declined%{self.user['username']}".encode())
        # Close the connection
        self.socket.close()
        self.socket = socket.socket()
        # Remove the invite from the DB
        self.server_communicator.dismiss_invite(self.user["username"])
        self.remove_button(inviter_name)

        self.update_screen()

    def remove_button(self, inviter_name):
        buttons = {}
        # Remove the invite buttons from the screen
        for button in self.buttons:
            if (
                button.text == "Accept"
                or button.text == "Reject"
                or inviter_name in button.text
                or button.text == "invitation!"
            ):
                # Don't add the button to the new buttons array
                continue
            else:
                buttons[button] = self.buttons[button]
        self.buttons = buttons

    def create_menu(self):
        """Creates the main menu screen and all it's components"""
        self.screen = pygame.display.set_mode((self.width, self.height))
        # Display the background image in case there is one
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        # Set up the buttons and display them

        button_width = 504
        button_height = 150
        cur_x = self.width // 2 - 258
        cur_y = self.height // 4 - button_height
        button_offset = button_height + 75
        cur_button_text = "sprint"
        self.create_button(
            (cur_x, cur_y),
            button_width,
            button_height,
            Colors.YELLOW_BUTTON,
            cur_button_text,
            func=self.sprint,
            info_text="Sprint is a gamemode in which the\ngoal is to play as fast as you can.\n"
            "You pick a number of lines and your\nscore is measured based on how fast\n"
            "you can destroy that many lines.",
        )

        cur_y += button_offset

        cur_button_text = "marathon"
        self.create_button(
            (cur_x, cur_y),
            button_width,
            button_height,
            Colors.DEEP_BLUE_BUTTON,
            cur_button_text,
            func=self.marathon,
            info_text="Marathon is a gamemode in which the\ngoal is to play as long as you can.\nEvery 10 lines "
            "the drop speed gets\nfaster and your score is measured\nbased on how long you've survived.",
        )
        cur_y += button_offset

        cur_button_text = "multiplayer"
        self.create_button(
            (cur_x, cur_y),
            button_width,
            button_height,
            Colors.PINKISH_BUTTON,
            cur_button_text,
            func=self.create_room_list,
            info_text="Multiplayer is a gamemode in which\nplayers compete against each other.\nEach line you destroy "
            'sends\n"garbage" lines to the opponent.\nYour goal is to make everyone\ntop out by sending '
            '"garbage".',
        )
        cur_y += button_offset

        cur_button_text = "leaderboard"
        self.create_button(
            (cur_x, cur_y),
            button_width,
            button_height,
            Colors.GREEN_BUTTON,
            cur_button_text,
            func=self.create_leaderboard,
            info_text="Top scores of all time\nin various categories",
            info_size=40,
        )

        name_width = 350
        name_height = 100
        cur_button_text = self.user["username"]
        name_font_size = 45
        if len(cur_button_text) > 7:
            name_font_size -= (len(cur_button_text) - 7) * 3 + 1

        self.create_button(
            (self.width - name_width - 5, self.height // 3 - 250),
            name_width,
            name_height,
            Colors.BLACK_BUTTON,
            cur_button_text,
            name_font_size,
            func=self.user_profile,
            args=(self.user["username"],),
        )

        # Settings button
        self.create_button(
            (10, 10),
            60,
            60,
            Colors.DEEP_BLUE_BUTTON,
            "⚙",
            text_size=50,
            func=self.settings,
        )

        # Sound button
        music_button = self.create_button(
            (75, 10),
            60,
            60,
            Colors.DEEP_BLUE_BUTTON,
            "♪" if self.cache["user"]["music"] else "⛔",
            50,
            Colors.GREEN if self.cache["user"]["music"] else Colors.RED,
        )

        self.buttons[music_button] = (self.toggle_sound, (music_button,))

        # Friends list screen
        friends_button_width = name_width // 7
        self.create_button(
            (self.width - name_width - friends_button_width, self.height // 3 - 250),
            friends_button_width,
            name_height,
            Colors.BLACK_BUTTON,
            "Ⓕ",
            func=self.friends_screen,
            args=("friends",),
        )

        # Request list screen
        self.create_button(
            (
                self.width - name_width - friends_button_width * 2,
                self.height // 3 - 250,
            ),
            friends_button_width,
            name_height,
            Colors.BLACK_BUTTON,
            "Ⓡ",
            func=self.friends_screen,
            args=("requests_sent",),
        )

        self.display_buttons()

    def toggle_sound(self, button):
        if button.text == "♪":
            button.text = "⛔"
            button.text_color = Colors.RED
            button.rendered_text = button.render_button_text()
            music = False
            pygame.mixer.pause()
        else:
            button.text = "♪"
            button.text_color = Colors.GREEN
            button.rendered_text = button.render_button_text()
            music = True
            pygame.mixer.unpause()

        # Update the user's music preference
        user = self.cache["user"]
        user["music"] = music
        self.cache["user"] = user
        threading.Thread(
            target=self.server_communicator.update_music, args=(user["username"], music)
        ).start()

    def settings(self):
        """A screen in which the user can change his settings"""
        settings_screen = SettingsScreen(
            self.server_communicator,
            self.cache,
            self.width,
            self.height,
            self.refresh_rate,
            self.background_path,
        )
        self.running = False
        settings_screen.run()
        self.cache = settings_screen.cache
        print(self.cache)
        self.on_menu_start()

    def friends_screen(self, type):
        friends_screen = FriendsScreen(
            self.cache["user"],
            self.server_communicator,
            self.cache,
            12,
            type,
            self.width,
            self.height,
            self.refresh_rate,
            self.background_path,
        )
        self.running = False
        friends_screen.run()
        self.cache = friends_screen.cache
        self.on_menu_start()

    def quit(self):
        self.buttons = {}
        self.textboxes = {}
        self.running = False
        self.server_communicator.update_online(self.user["username"], False)

    def create_leaderboard(self):
        leaderboard = LeaderboardScreen(
            self.cache["user"],
            self.server_communicator,
            self.cache,
            4,
            self.width,
            self.height,
            self.refresh_rate,
            self.background_path,
        )
        self.running = False
        leaderboard.run()
        # Update the cache
        self.cache = leaderboard.cache
        self.on_menu_start()

    def user_profile(self, username):
        profile = UserProfile(
            self.cache["user"],
            username,
            self.server_communicator,
            self.width,
            self.height,
            self.refresh_rate,
            self.background_path,
            user_profile=self.cache.get(username),
        )
        self.running = False
        profile.run()
        # Update the cache
        self.cache["user"] = profile.user
        self.cache[username] = profile.profile

        self.on_menu_start()

    def create_room_list(self):
        room_screen = RoomsScreen(
            self.cache["user"],
            self.server_communicator,
            self.cache,
            3,
            self.width,
            self.height,
            self.refresh_rate,
            self.background_path,
        )
        self.running = False
        room_screen.run()
        # Update the cache
        self.cache = room_screen.cache

        self.on_menu_start()

    def multiplayer(self):
        """Create the multiplayer screen - set up the correct buttons"""
        self.buttons = {}
        self.reset_textboxes()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))

        self.create_button(
            (self.width // 2 - 250, self.height // 2 - 200),
            500,
            200,
            Colors.WHITE_BUTTON,
            "Room List",
            text_color=Colors.GREY,
            func=self.create_room_list,
        )

        self.display_buttons()
        self.display_textboxes()
        pygame.display.flip()

    def old_multiplayer(self):
        """Create the multiplayer screen - set up the correct buttons"""
        self.buttons = {}
        self.reset_textboxes()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        self.create_textbox(
            (self.width // 2 - 250, self.height // 2 - 200),
            500,
            200,
            Colors.WHITE_BUTTON,
            "Opponent Name",
            text_color=Colors.GREY,
        )

        cur_button_text = "Challenge"
        self.create_button(
            (self.width // 2 - 250, (self.height // 3) * 2),
            500,
            200,
            Colors.BLACK_BUTTON,
            cur_button_text,
            #            func=self.multiplayer_continue
        )
        self.display_buttons()
        self.display_textboxes()
        pygame.display.flip()

    def sprint(self):
        """Create the sprint screen - set up the correct buttons"""
        self.buttons = {}
        self.reset_textboxes()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))

        function_button_width = 75
        function_button_height = 75
        # Create the back button
        self.create_button(
            (self.width - function_button_width, 0),
            function_button_width,
            function_button_height,
            Colors.BLACK_BUTTON,
            "->",
            55,
            Colors.WHITE,
            func=self.quit,
        )

        self.create_button(
            (self.width // 2 - 257, self.height // 8 - 85),
            501,
            200,
            Colors.YELLOW_BUTTON,
            "20L",
            func=self.start_game,
            args=("sprint", 20),
        )
        self.create_button(
            (self.width // 2 - 257, self.height // 8 * 3 - 81),
            501,
            200,
            Colors.YELLOW_BUTTON,
            "40L",
            func=self.start_game,
            args=("sprint", 40),
        )
        self.create_button(
            (self.width // 2 - 257, self.height // 8 * 5 - 86),
            501,
            200,
            Colors.YELLOW_BUTTON,
            "100L",
            func=self.start_game,
            args=("sprint", 100),
        )
        self.create_button(
            (self.width // 2 - 257, self.height // 8 * 7 - 85),
            501,
            200,
            Colors.YELLOW_BUTTON,
            "1000L",
            func=self.start_game,
            args=("sprint", 1000),
        )
        self.display_buttons()
        pygame.display.flip()

    def marathon(self):
        """Create the marathon screen - set up the correct buttons"""
        self.buttons = {}
        self.reset_textboxes()
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))

        function_button_width = 75
        function_button_height = 75
        # Create the back button
        self.create_button(
            (self.width - function_button_width, 0),
            function_button_width,
            function_button_height,
            Colors.BLACK_BUTTON,
            "->",
            55,
            Colors.WHITE,
            func=self.quit,
        )

        title_width = self.width
        title_height = 200
        cur_x = 0
        cur_y = 0
        # Create the screen title
        self.create_button(
            (cur_x, cur_y),
            title_width,
            title_height,
            Colors.BLACK_BUTTON,
            "CHOOSE A STARTING LEVEL",
            70,
            Colors.WHITE,
            text_only=True,
        )

        button_height = 200
        button_width = 200
        row_height = self.height // 2 - button_height
        row_starting_width = self.width // 10
        # First line of buttons
        for i in range(5):
            btn = self.create_button(
                (row_starting_width * (3 + (i - 1) * 2) - 100, row_height),
                button_width,
                button_height,
                Colors.DEEP_BLUE_BUTTON,
                str(i),
                func=self.start_game,
                args=("marathon", i),
            )
            if i % 2 == 0:
                btn.color = btn.get_action_color(btn.color, alpha=15)
        # Second line of buttons
        row_height = row_height + button_height + 100
        for i in range(5):
            btn = self.create_button(
                (row_starting_width * (3 + (i - 1) * 2) - 100, row_height),
                button_width,
                button_height,
                Colors.DEEP_BLUE_BUTTON,
                str(i + 5),
                func=self.start_game,
                args=("marathon", i + 5),
            )
            if i % 2 == 1:
                btn.color = btn.get_action_color(btn.color, alpha=15)

        self.display_buttons()
        pygame.display.flip()

    def start_game(self, mode, lines_or_level):
        """Start a generic game, given a mode and the optional starting lines or starting level"""
        # Stop all music
        for sound in self.BACKGROUND_MUSIC.values():
            sound.stop()
        # Close the main menu
        self.running = False
        # Create the game
        self.buttons = {}
        self.reset_textboxes()
        game = TetrisGame(
            500 + 200,
            1000,
            mode,
            self.server_communicator,
            self.cache["user"],
            75,
            lines_or_level=int(lines_or_level),
        )
        game.run()
