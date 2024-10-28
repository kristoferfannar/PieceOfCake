import constants
import numpy as np
from players.g2.helpers import *

class EvenCuts:
    def __init__(self, requests, cake_width, cake_len):
        self.phase = "HORIZONTAL"
        self.direction = ""
        self.n = num_requests
        self.cake_width = cake_width
        self.cake_len = cake_len
        self.s_x = cake_width / np.sqrt(self.n)
        self.s_y = cake_len / np.sqrt(self.n)
        self.move_queue = []

    def horizontal_to_vertical(self, pos):
        self.phase = "VERTICAL"
        if pos[0] != 0:
            self.s_x = 0 - self.s_x
        self.move_queue.extend(sneak(pos, [pos[0] + self.s_x, self.cake_len], self.cake_width, self.cake_len))
        self.move_queue.append([pos[0] + self.s_x, 0])

    def horizontal_cut(self, pos):
        self.move_queue.extend(sneak(pos, [pos[0], pos[1] + self.s_y], self.cake_width, self.cake_len))
        if pos[0] == 0:
            opposite = self.cake_width
        else:
            opposite = 0
        self.move_queue.append([opposite, round(pos[1] + self.s_y, 2)])

    def vertical_cut(self, pos):
        self.move_queue.extend(sneak(pos, [pos[0] + self.s_x, pos[1]], self.cake_width, self.cake_len))
        if pos[1] == 0:
            opposite = self.cake_len
        else:
            opposite = 0
        self.move_queue.append([new_x, opposite])

    def even_cuts(self, pos):
        """
        Adds moves to the merge queue that will cut the cake into even slices.
        """
        if self.phase == "HORIZONTAL":
            if pos[1] + self.s_y < self.cake_len:
                self.horizontal_cut(pos)
            else:
                self.horizontal_to_vertical(pos)
        else:
            if pos[0] + self.s_x in range(0.01, self.cake_width):
                self.vertical_cut(pos)
            else:
                self.phase = "DONE"
        return

    def move(self, turn_number, cur_pos):
        if turn_number == 1:
            return constants.INIT, [0.01, 0]
        
        if turn_number == 2:
            self.move_queue.append([0, self.s_y])
            self.move_queue.append([self.cake_width, self.s_y])
        elif len(self.move_queue) == 0 and self.phase != "DONE":
            self.even_cuts(cur_pos)

        if len(self.move_queue) > 0:
            next_val = self.move_queue.pop(0)
            cut = [round(next_val[0], 2), round(next_val[1], 2)]
            return constants.CUT, cut

        return None