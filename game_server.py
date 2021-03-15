import pickle
import random
import socket
import threading
import time
from select import select
from typing import List

from server_communicator import ServerCommunicator


class GameServer:
    SERVER_PORT = 44444

    def __init__(self, server_ip):
        self.client_list = []
        self.players = {}
        self.players_wins = {}
        self.ready_clients = []
        self.responses_list = []
        self.data_dict = {}
        self.game_running = False
        self.room_name = ""

        self.server_socket = socket.socket()
        self.server_ip = server_ip
        self.server_communicator = ServerCommunicator("127.0.0.1", "8000")

    def run(self):
        self.server_socket.bind((self.server_ip, self.SERVER_PORT))
        self.server_socket.listen(1)
        # Always accept new clients
        threading.Thread(target=self.connect_clients).start()
        while True:
            if not self.client_list:
                continue
            read_list, write_list, _ = select(self.client_list, self.client_list, [])
            self.handle_read(read_list)
            self.handle_write(write_list)
            if len(self.ready_clients) < 2:
                continue
            else:
                time_at_start = str(time.time())
                # Notify each client of game start
                for client in self.ready_clients:
                    threading.Thread(target=self.notify_client_of_game_start, args=(client, time_at_start,)).start()
                # Start the game
                self.game_running = True
            # Pass information between the players
            while self.game_running:
                read_list, write_list, _ = select(
                    self.client_list, self.client_list, []
                )
                self.handle_read(read_list)
                self.handle_write(write_list)

    @staticmethod
    def notify_client_of_game_start(client, time_at_start):
        client.send("started".encode())
        client.recv(1024)
        client.send(str(time_at_start).encode())

    def handle_read(self, read_list: List[socket.socket]):
        """Handles reading from the clients"""
        for client in read_list:
            data = client.recv(25600)

            if not self.game_running:
                try:
                    data = data.decode()
                # Info from the last game
                except UnicodeDecodeError:
                    print("skipped")
                    continue

                self.handle_message(data, client)

            # Game in progress
            else:
                try:
                    data = pickle.loads(data)
                except pickle.UnpicklingError:
                    data = data.decode()
                    self.handle_message(data, client)
                    continue
                # Game ended, someone won
                if data[0] == "W":
                    self.data_dict = {}
                    for other_client in self.client_list:
                        if other_client is client:
                            continue
                        other_client.send(pickle.dumps(["Win", 0]))
                    client.send(pickle.dumps(["Lose", 0]))
                    self.game_over()

                # Send the screen from one client to another
                else:
                    for other_client in self.client_list:
                        if other_client is client:
                            continue
                        self.data_dict[other_client] = pickle.dumps(data)

    def handle_message(self, data, client):
        # The client pressed the ready button
        if data[0:len("Ready%")] == "Ready%":
            if client in self.ready_clients:
                self.ready_clients.remove(client)
            else:
                self.ready_clients.append(client)

        # Client disconnected
        elif data == "disconnect":
            self.client_list.remove(client)
            player_name = self.players[client]
            self.players.pop(client)
            if client in self.ready_clients:
                self.ready_clients.remove(client)
            self.players_wins.pop(player_name)

            for other_client in self.client_list:
                other_client.send(f"!{player_name}".encode())
            # Update the removed player in the database
            threading.Thread(target=self.update_player_num).start()
            return
        # If it's just a normal message, send it to every client
        for other_client in self.client_list:
            self.data_dict[other_client] = data.encode()

    # TODO and also fix room crashing after 2 games
    def game_over(self):
        """End the game"""
        self.game_running = False
        for client in self.client_list:
            client.recv(25600)
        self.data_dict = {}
        self.ready_clients = []

    def handle_write(self, write_list: List[socket.socket]):
        """Handles writing from the client"""
        # Send every client their foe's screen
        for client in write_list:
            foe_data = self.data_dict.get(client)
            # A screen is available to send
            if foe_data:
                self.data_dict.pop(client)
                client.send(foe_data)

    def connect_clients(self):
        while True:
            client, addr = self.server_socket.accept()

            # Send the client the player name list
            client.send(pickle.dumps(self.players_wins))
            # Receive ok from client
            client.recv(1024)
            # Send the client all ready players
            ready_players = [self.players[client] for client in self.ready_clients]
            client.send(pickle.dumps(ready_players))

            # Add the client to the relevant lists
            self.client_list.append(client)
            name = client.recv(1024).decode()
            self.players[client] = name
            self.players_wins[name] = 0

            for client in self.client_list:
                client.send(name.encode())

            threading.Thread(target=self.update_player_num).start()

    def update_player_num(self):
        print(len(self.client_list))
        self.server_communicator.update_player_num(self.server_ip, len(self.client_list))

    def create_db_post(self, ip: str, min_apm: int = 0, max_apm: int = 999, private: bool = False) -> dict:
        """Returns a db post with the given parameters"""
        return {
            "_id": self.server_communicator.estimated_document_count(),
            "type": "room",
            "name": "Test room",
            "ip": ip,
            "player_num": 0,
            "min_apm": min_apm,
            "max_apm": max_apm,
            "private": private
        }


if __name__ == "__main__":
    ip = "10.100.102.17"
    #ip = "172.19.230.76"
    server = GameServer(ip)
    # Add the room to the database
    #server.server_communicator.create_room(server.create_db_post(ip))
    server.run()
