from tildagonos import tildagonos, led_colours
import imu
import app
from events.input import Buttons, BUTTON_TYPES
from app_components import Notification, clear_background

BACKGROUND_COLOUR = (0.5, 0.5, 0.5)
LINE_COLOUR = (0, 0, 0)
POINTER_COLOUR = (1, 0, 0)
LIFTED_POINTER_COLOUR = (0, 1, 0.3)
SCREEN_RADIUS = 120
MIN_SPEED = 1
MAX_SPEED = 5
ACCELERATION = 0.5
SHAKES_TO_CLEAR = 10
Y = 1
Z = 2

class EchtASketch(app.App):
    def __init__(self):
        super().__init__()
        self.overlays = [LineSegment((0,0), (0,0), LINE_COLOUR)]
        self.button_states = Buttons(self)
        self.current_direction = "R"
        self.state = "RightWayUp"
        self.shake_count = 0
        self.speed = MIN_SPEED
        self.etching = True
        self.notification = Notification("Shake upside down to clear")

    def update(self, delta):
        if self.notification:
            self.notification.update(delta/2)

        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            # The button_states do not update while you are in the background.
            # Calling clear() ensures the next time you open the app, it doesn't still
            # see the cancel button as pressed.
            self.button_states.clear()
            # If there's a notification, clear it. Otherwise exit the app.
            if self.notification :
                self.notification = None
            else:
                self.minimise()
            
        if (self.state == "RightWayUp"):
            self.check_for_stylus_move()
        else:
            # Upside down. Check for shakes
            self.check_for_shakes()

    def check_for_stylus_move(self):
        accel = imu.acc_read()
        if (accel[Z] < 0): # Upside down
            self.shake_count = 0
            if (accel[Y] < 0):
                self.state = "TiltedLeft"
            else: 
                self.state = "TiltedRight"
        else:       
            # Not upside down. 
            self.state = "RightWayUp"
            # Which direction are we pointing?
            # When the direction changes, call that a new line segment.
            # Store all the line segments for redrawing every frame.
            direction = ""
            new_coord = self.overlays[-1].end
            if self.button_states.get(BUTTON_TYPES["CONFIRM"]): # Using confirm as the right button.
                new_coord = (new_coord[0] + self.speed, new_coord[1])
                direction = direction + "R"
            if self.button_states.get(BUTTON_TYPES["UP"]):
                new_coord = (new_coord[0], new_coord[1] - self.speed)
                direction = direction + "U"
            if self.button_states.get(BUTTON_TYPES["LEFT"]):
                new_coord = (new_coord[0] - self.speed, new_coord[1])
                direction = direction + "L"
            if self.button_states.get(BUTTON_TYPES["DOWN"]):
                new_coord = (new_coord[0], new_coord[1] + self.speed)
                direction = direction + "D"
            # Don't clear the button state for those things.
            # Allow lifting the stylus off the screen. A bit cheaty.
            if self.button_states.get(BUTTON_TYPES["RIGHT"]):   # Using right as pen up/down
                self.etching = not self.etching
                direction = direction + "!" # Treat this as a change of direction.
                # Clear the button state here - we only want to register one of these key presses
                self.button_states.clear()

            # Before we use that new coord, see if we've bumped up against the edge of the display.
            gone_too_far = ((new_coord[0] * new_coord[0]) + (new_coord[1] * new_coord[1])) >= (SCREEN_RADIUS * SCREEN_RADIUS)
            if (not gone_too_far):
                # Do we have a direction, and if so, is it different from the previous one?
                if (direction != ""):
                    if (self.current_direction != direction and self.overlays[-1].start != self.overlays[-1].end):
                        # We've changed direction. So that's one straight line segment created. Start the next one.
                        self.overlays.append(LineSegment(self.overlays[-1].end, self.overlays[-1].end, LINE_COLOUR))
                    self.current_direction = direction
                    self.speed = min(self.speed + ACCELERATION, MAX_SPEED)
                else:
                    self.speed = MIN_SPEED

                self.overlays[-1].end = new_coord
                if (not self.etching):
                    self.overlays[-1].start = self.overlays[-1].end


    def check_for_shakes(self):
        accel = imu.acc_read()
        if (accel[Z] > 0): # Gone the right way up.
            self.state = "RightWayUp"
        else:
            if (self.state == "TiltedLeft"):
                if (accel[Y] > 0):
                    self.state = "TiltedRight"
                    self.shake_count = self.shake_count + 1
                    if (self.shake_count >= SHAKES_TO_CLEAR):
                        current_point = self.overlays[-1].end
                        self.overlays = [LineSegment(current_point, current_point, LINE_COLOUR)]
                    else:
                        degree_of_fading = self.shake_count/SHAKES_TO_CLEAR
                        for line_segment in self.overlays:
                            faded_colour = ((1 - degree_of_fading) * line_segment.colour[0]) + (degree_of_fading * BACKGROUND_COLOUR[0])                                
                            line_segment.set_colour((faded_colour, faded_colour, faded_colour))
            else:
                # Last tilt was right. Check for a left tilt.
                if (accel[Y] < 0):
                    self.state = "TiltedLeft"


    def draw(self, ctx):
        ctx.save()
        # Clear the background
        ctx.rgb(*BACKGROUND_COLOUR)
        ctx.rectangle(-SCREEN_RADIUS, -SCREEN_RADIUS, SCREEN_RADIUS*2, SCREEN_RADIUS*2).fill()
        # Draw the notification if there is one.
        if self.notification:
            self.notification.draw(ctx)

        # Draw the line segments
        self.draw_overlays(ctx)

        # And draw the etching pointer
        if self.etching:
            ctx.rgb(*POINTER_COLOUR)
        else:
            ctx.rgb(*LIFTED_POINTER_COLOUR)
        ctx.rectangle(self.overlays[-1].end[0], self.overlays[-1].end[1], 1, 1)
        ctx.stroke()
        ctx.restore()

class LineSegment():
    def __init__(self, start_coords, end_coords, colour):
        self.start = start_coords
        self.end = end_coords
        self.colour = colour

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(*self.colour)
        ctx.begin_path()
        ctx.move_to(*self.start)
        ctx.line_to(*self.end)
        ctx.stroke()
        ctx.restore()

    def set_colour(self, colour):
        self.colour = colour

__app_export__ = EchtASketch
