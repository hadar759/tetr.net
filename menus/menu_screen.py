import socket
from typing import Optional, Dict, Tuple

import pygame
from requests import get

from menus.button import Button
from tetris.colors import Colors
from menus.text_box import TextBox


class MenuScreen:
    BUTTON_PRESS = pygame.MOUSEBUTTONDOWN

    def __init__(
        self,
        width: int,
        height: int,
        refresh_rate: int = 60,
        background_path: Optional[str] = None,
    ):
        self.width, self.height = width, height
        self.refresh_rate = refresh_rate
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.background_image = (
            pygame.image.load(background_path) if background_path else None
        )
        self.background_path = background_path
        self.running = True
        self.buttons: Dict[Button, callable] = {}
        self.textboxes: Dict[TextBox, str] = {}
        self.actions = {}
        self.mouse_pos = ()

    def run(self):
        self.update_screen()

        for event in pygame.event.get():
            # Different event, but mouse pos was initiated
            if self.mouse_pos:
                self.handle_events(event)

    def handle_events(self, event):
        if event.type == pygame.QUIT:
            self.quit()
            pygame.quit()
            quit()

        # If the user typed something
        if event.type == pygame.KEYDOWN:
            for textbox in self.textboxes.keys():
                if textbox.active:
                    self.textbox_key_actions(textbox, event)
                    break

        # In case the user pressed the mouse button
        if event.type == self.BUTTON_PRESS and event.button == 1:
            for button in reversed(self.buttons):
                # Check if the click is inside the button area (i.e. the button was clicked)
                # Otherwise skip
                if not button.inside_button(self.mouse_pos):
                    continue
                # Change the button color
                button.clicked(self.screen)
                # Get the correct response using to the button
                func, args = self.buttons[button]
                # User pressed a button with no response function
                if not func:
                    continue
                func(*args)
                break

            for textbox in self.textboxes.keys():
                # Check if the click is inside the textbox area (i.e. whether the textbox was clicked)
                if textbox.inside_button(self.mouse_pos):
                    # Make the textbox writeable
                    textbox.active = True
                else:
                    textbox.active = False

    def quit(self):
        self.running = False

    @staticmethod
    def get_outer_ip():
        return get("https://api.ipify.org").text

    @staticmethod
    def get_inner_ip():
        return socket.gethostbyname(socket.gethostname())

    def create_button(
        self,
        starting_pixel: Tuple[int, int],
        width: int,
        height: int,
        color: Dict,
        text: str,
        text_size: int = 45,
        text_color: Tuple[int, int, int] = Colors.WHITE,
        transparent: bool = False,
        func: callable = None,
        text_only: bool = False,
        args: Tuple = (),
        border_size: int = 10,
        clickable: bool = True,
    ):
        """Creates a new button and appends it to the button dict"""
        button = Button(
            starting_pixel,
            width,
            height,
            color,
            text,
            text_size,
            text_color,
            transparent,
            text_only,
            border_size,
            clickable,
        )
        self.buttons[button] = (func, args)

        return button

    def create_textbox(
        self,
        starting_pixel: Tuple[int, int],
        width: int,
        height: int,
        color: int,
        text: str,
        text_size: int = 45,
        text_color: Tuple[int, int, int] = Colors.WHITE,
        transparent: bool = False,
        text_only: bool = False,
        is_pass: bool = False,
    ) -> TextBox:
        """Creates a new textbox and appends it to the textbox dict"""
        box = TextBox(
            starting_pixel,
            width,
            height,
            color,
            text,
            text_size,
            text_color,
            transparent,
            text_only,
            is_pass,
        )
        self.textboxes[box] = ""
        return box

    def create_popup_button(self, text):
        button_width = self.width // 2
        button_height = self.height // 3
        # Place the button in the middle of the screen
        mid_x_pos = self.width // 2 - (button_width // 2)

        self.create_button(
            (mid_x_pos, self.height // 2 - button_height),
            button_width,
            button_height,
            Colors.BLACK_BUTTON,
            text,
            38,
            text_color=Colors.RED,
            func=self.buttons.popitem,
        )

    def textbox_key_actions(self, textbox: TextBox, event: pygame.event.EventType):
        textbox_text = self.textboxes[textbox]

        # BACKSPACE/DELETE
        if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
            # We haven't entered any text
            if textbox_text == textbox.text:
                return
            # Last letter
            if len(textbox_text) <= 1:
                self.textboxes[textbox] = textbox.text
            # Just regular deleting
            else:
                self.textboxes[textbox] = textbox_text[:-1]

        # ENTER
        elif event.key == 13 or event.key == pygame.K_TAB:
            # Move to the next textbox
            self.textboxes[textbox] = self.textboxes[textbox].rstrip()
            textbox.active = False
            next_textbox = self.get_next_in_dict(self.textboxes, textbox)
            try:
                next_textbox.active = True
            # In case there aren't any more textboxes
            except AttributeError:
                pass

        # TEXT
        else:
            if self.textboxes[textbox] == textbox.text:
                self.textboxes[textbox] = ""
            self.textboxes[textbox] += event.unicode

    def display_buttons(self):
        """Display all buttons on the screen"""
        for button in self.buttons.keys():
            if not button.transparent:
                if not button.text_only:
                    button.color_button(self.screen)
                button.show_text_in_button(self.screen)

    @staticmethod
    def get_next_in_dict(dict: Dict, given_key):
        key_index = -999

        for index, key in enumerate(dict.keys()):
            if key == given_key:
                key_index = index

            if index == key_index + 1:
                return key

    def display_textboxes(self):
        """Display all buttons on the screen"""
        for textbox in self.textboxes.keys():
            if not textbox.transparent:
                x = textbox.starting_x
                y = textbox.starting_y
                if not textbox.text_only:
                    textbox.color_button(self.screen)
                self.textboxes[textbox] = textbox.show_text_in_textbox(
                    self.textboxes[textbox], self.screen
                )

    def show_text_in_buttons(self):
        """Display the button's text for each of the buttons we have"""
        for button in self.buttons.keys():
            button.show_text_in_button(self.screen)

    def reset_textboxes(self):
        for textbox in self.textboxes:
            self.textboxes[textbox] = ""
            textbox.rendered_text = textbox.render_button_text(
                textbox.text, textbox.text_size, textbox.text_color
            )

    def update_screen(self):
        """Displays everything needed to be displayed on the screen"""
        # Display the background image in case there is one
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        self.display_textboxes()
        self.display_buttons()
        self.drawings()
        pygame.display.flip()

    def drawings(self):
        pass

    def update_mouse_pos(self):
        while self.running:
            self.mouse_pos = pygame.mouse.get_pos()
