from typing import List

import pygame

from .tetris_piece import Piece


class SPiece(Piece):
    PIVOT_POINT = 1

    def __init__(self, skin: int = 0, pos: List[List] = None):
        self.sprite = pygame.image.load(rf"./resources/spiece-sprite{skin}.png")
        if not pos:
            pos = [[1, 3], [1, 4], [0, 4], [0, 5]]
        super().__init__(self.sprite, pos)
