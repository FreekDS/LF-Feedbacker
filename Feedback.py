import pygame
from threading import Thread
from flask import Flask, Response
import glob

BACKGROUND = (42, 60, 247)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)


def center_rect(image):
    rect = image.get_rect()
    w, h = pygame.display.get_surface().get_size()
    x = (w - rect.w) / 2
    y = (h - rect.h) / 2
    rect.left, rect.top = (x, y)
    return rect


def update_alpha(alpha, value):
    alpha += value
    return min(max(alpha, 0), 255)


class SlideShow:
    def __init__(self, path: str, default):

        images = glob.glob(path + '/*.png')

        self.images = [pygame.image.load(path) for path in images]
        self.default = pygame.image.load(default).convert()
        self.draw_default = True
        self._curr = 0
        self.start = pygame.time.get_ticks()

    @property
    def current_image(self):
        return self.images[self._curr]

    def _update_ptr(self):
        self._curr += 1
        if self._curr >= len(self.images):
            self._curr = 0

    @staticmethod
    def blit_alpha(target, source, location, opacity):
        x = location[0]
        y = location[1]
        temp = pygame.Surface((source.get_width(), source.get_height())).convert()
        temp.blit(target, (-x, -y))
        temp.blit(source, (0, 0))
        temp.set_alpha(opacity)
        target.blit(temp, location)

    def draw(self, screen):
        current_sponsor = self.images[self._curr]

        end = pygame.time.get_ticks()
        elapsed = round((end - self.start) / 1000, 2)

        if self.draw_default:
            screen.blit(self.default, center_rect(self.default))
            if elapsed > 10:
                screen.fill(BACKGROUND)
                self.draw_default = False
                self.start = pygame.time.get_ticks()
        else:
            screen.blit(current_sponsor, center_rect(current_sponsor))
            if elapsed > 5:
                screen.fill(BACKGROUND)
                self.draw_default = True
                self._update_ptr()
                self.start = pygame.time.get_ticks()
        self.start += 1


class Background:
    def __init__(self, image_file):
        self.image = pygame.image.load(image_file)
        self.rect = self.image.get_rect()
        # put in center
        w, h = pygame.display.get_surface().get_size()
        x = (w - self.rect.w) / 2
        y = (h - self.rect.h) / 2
        self.rect.left, self.rect.top = (x, y)


def flask_resource(func):
    def wrapper(*args, **kwargs):
        answer = func(*args, **kwargs)
        response = Response(answer, status=200, headers={})
        return response

    return wrapper


class Feedback:
    def __init__(self, fullscreen=False):
        self.app = Flask(__name__)
        self.server = None

        pygame.init()
        pygame.display.set_caption("Scanning feedback")
        if fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((845, 480))
        self.bg = Background("bg.png")
        self.slideshow = SlideShow("sponsors/", "bg.png")
        self.clock = pygame.time.Clock()
        self._quit = False

        self._display_active = False
        self._activation_time = 0
        self._time_active = 0
        self.color = BACKGROUND

        self.font = pygame.font.Font('freesansbold.ttf', 78)
        self.text = None
        self.textRec = None

    def scan_event(self, color, text_color, text):
        self.color = color
        self._display_active = True
        self.screen_update()
        self.text = self.font.render(text, False, text_color)
        self.textRec = self.text.get_rect()
        self.textRec.center = (845 / 2, 480 / 2)
        self.screen.blit(self.text, self.textRec)
        self._activation_time = pygame.time.get_ticks()

    @flask_resource
    def scan_success(self):
        self.scan_event(GREEN, BACKGROUND, 'SUCCESS')
        return "Scan success"

    @flask_resource
    def scan_failure(self):
        self.scan_event(RED, BACKGROUND, 'FAIL')
        return "Scan failure"

    @flask_resource
    def default(self):
        return "home"

    def add_all_rules(self):
        self.app.add_url_rule('/success', 'success', self.scan_success)
        self.app.add_url_rule('/failure', 'failure', self.scan_failure)
        self.app.add_url_rule('/', 'default', self.default)

    def screen_update(self):
        self.screen.fill(self.color)
        if not self._display_active:
            self.screen.blit(self.bg.image, self.bg.rect)

    def run_pygame(self):
        global BACKGROUND

        for _ in range(0, 2):
            self.screen_update()
            BACKGROUND = self.screen.get_at(self.bg.rect.midleft)[:-1]
            self.color = BACKGROUND

        while not self._quit:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self._quit = True

            if self._display_active:
                self._time_active = pygame.time.get_ticks() - self._activation_time
            else:
                self.slideshow.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(20)

            if self._time_active >= 1000:
                self.color = BACKGROUND
                self._display_active = False
                self._time_active = 0

        self.exit()

    def start(self):
        self.add_all_rules()
        kwargs = {
            'use_reloader': False,
        }
        self.server = Thread(target=self.app.run, kwargs=kwargs)
        self.server.setDaemon(True)
        self.server.start()
        self.run_pygame()

    @staticmethod
    def exit():
        exit(0)


if __name__ == '__main__':
    f = Feedback()
    f.start()
