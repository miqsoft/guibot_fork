# Copyright 2013 Intranet AG / Thomas Jarosch
#
# guibender is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibender is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibender.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import time

from autopy import mouse
from autopy import bitmap

# interconnected classes - import only their modules
# to avoid circular reference
import screen
import match, sys

from errors import *
from location import Location
from image import Image

class Region(object):
    def __init__(self, xpos=0, ypos=0, width=0, height=0):
        self.screen = screen.Screen()
        self.last_match = None

        self.xpos = xpos
        self.ypos = ypos

        if width == 0:
            self.width = self.screen.get_width()
        else:
            self.width = width

        if height == 0:
            self.height = self.screen.get_height()
        else:
            self.height = height

        self._ensure_screen_clipping()

    def _ensure_screen_clipping(self):
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()

        if self.xpos < 0:
            self.xpos = 0

        if self.ypos < 0:
            self.ypos = 0

        if self.xpos > screen_width:
            self.xpos = screen_width -1

        if self.ypos > screen_height:
            self.ypos = screen_height -1

        if self.xpos + self.width > screen_width:
            self.width = screen_width - self.xpos

        if self.ypos + self.height > screen_height:
            self.height = screen_height - self.ypos

    def get_x(self):
        return self.xpos

    def get_y(self):
        return self.ypos

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_center(self):
        xpos = (self.width - self.xpos) / 2
        ypos = (self.height - self.ypos) / 2

        return Location(xpos, ypos)

    def get_top_left(self):
        return Location(self.xpos, self.ypos)

    def get_top_right(self):
        return Location(self.xpos + self.width, self.ypos)

    def get_bottom_left(self):
        return Location(self.xpos, self.ypos + self.height)

    def get_bottom_right(self):
        return Location(self.xpos + self.width, self.ypos + self.height)

    def nearby(self, range=50):
        new_xpos = self.xpos - range
        if new_xpos < 0:
            new_xpos = 0

        new_ypos = self.ypos - range
        if new_ypos < 0:
            new_ypos = 0

        new_width = self.width + range + self.xpos - new_xpos
        new_height = self.height + range + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, new_ypos, new_width, new_height)

    def above(self, range=0):
        if range == 0:
            new_ypos = 0
            new_height = self.ypos + self.height
        else:
            new_ypos = self.ypos - range
            if new_ypos < 0:
                new_ypos = 0

            new_height = self.height + self.ypos - new_ypos

        # Final clipping is done in the Region constructor
        return Region(self.xpos, new_ypos, self.width, new_height)

    def below(self, range=0):
        if range == 0:
            range = self.screen.get_height()

        new_height = self.height + range

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, self.width, new_height)

    def left(self, range=0):
        if range == 0:
            new_xpos = 0
            new_width = self.xpos + self.width
        else:
            new_xpos = self.xpos - range
            if new_xpos < 0:
                new_xpos = 0

            new_width = self.width + self.xpos - new_xpos

        # Final clipping is done in the Region constructor
        return Region(new_xpos, self.ypos, new_width, self.height)

    def right(self, range=0):
        if range == 0:
            range = self.screen.get_width()

        new_width = self.width + range

        # Final clipping is done in the Region constructor
        return Region(self.xpos, self.ypos, new_width, self.height)

    def get_last_match(self):
        return self.last_match

    def find(self, image, timeout=10):
        # Load image if needed
        if isinstance(image, basestring):
            image = Image(image)

        # TODO: Factor out backend and remove loading from file
        autopy_needle = bitmap.Bitmap.open(image.get_filename())
        autopy_tolerance = 1.0 - image.get_similarity()

        timeout_limit = time.time() + timeout
        while True:
            # TODO: Factor out autopy code
            # Remove temporary conversion code using files.
            # This is just an intermediate step for the backend refactoring
            self.screen.capture().save('/tmp/guibender_temp_screenshot.png')
            autopy_screenshot = bitmap.Bitmap.open('/tmp/guibender_temp_screenshot.png')

            coord = autopy_screenshot.find_bitmap(autopy_needle, autopy_tolerance, ((self.xpos, self.ypos), (self.width, self.height)))
            if coord is not None:
                self.last_match = match.Match(coord[0], coord[1], image)
                return self.last_match

            if time.time() > timeout_limit:
                # TODO: Turn this into a setting / make it optional
                autopy_screenshot.save('/tmp/guibender_last_finderror.png')
                autopy_needle.save('/tmp/guibender_last_finderror_needle.png')

                break

            # don't hog the CPU
            # TODO: Make 'rescan speed' configurable
            time.sleep(0.2)

        raise FindError()

    def exists(self, image, timeout=0):
        try:
            return self.find(image, timeout)
        except:
            pass

        return None

    def wait(self, image, timeout=30):
        return self.find(image, timeout)

    def wait_vanish(self, image, timeout=30):
        expires = time.time() + timeout
        while time.time() < expires:
            if self.exists(image, 0) is None:
                return True

            # don't hog the CPU
            time.sleep(0.2)

        # image is still there
        return False

    def _move_mouse(self, xpos_or_location, ypos=0):
        try:
            # Note: Sometimes this is not pixel perfect.
            # Need to investigate the autopy source later on
            mouse.smooth_move(xpos_or_location.get_x(), xpos_or_location.get_y())
            # mouse.move(xpos_or_location.get_x(), xpos_or_location.get_y())
        except AttributeError:
            mouse.smooth_move(xpos_or_location, ypos)

    def get_mouse_location(self):
        autopy_pos = mouse.get_pos()
        return Location(autopy_pos[0], autopy_pos[1])

    def hover(self, image_or_location):
        # Handle Location
        try:
            self._move_mouse(image_or_location.get_x(), image_or_location.get_y())
            return None
        except AttributeError:
            pass

        # Find image
        match = self.find(image_or_location)
        self._move_mouse(match.get_target())

        return match

    def click(self, image_or_location):
        match = self.hover(image_or_location)
        mouse.click()
        return match

    def right_click(self, image_or_location):
        match = self.hover(image_or_location)
        mouse.click(mouse.RIGHT_BUTTON)
        return match

    def double_click(self, image_or_location):
        match = self.hover(image_or_location)

        mouse.click()
        # TODO: Make double click speed configurable
        time.sleep(0.1)
        mouse.click()

        return match

    # TODO: Implement key modifiers like SHIFT
    def write(self, image_or_location, text):
        # TODO: Implement me
        raise GuiBenderError()

    # TODO: Implement key modifiers like SHIFT
    # Press key combinations
    def press(self, image_or_location, text):
        # TODO: Implement me
        raise GuiBenderError()

    # List of API functions to implement:
    #
    # find_all(Image or filename)
    # wait_vanish(Image or filename, seconds)
    #
    # drag_drop(image, image, key_modifiers)
    # drag(image)
    # dropAt(image)
    #
