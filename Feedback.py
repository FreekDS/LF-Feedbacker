import pygame
from threading import Thread
from flask import Flask, Response

BACKGROUND = (42, 60, 247)
GREEN = (0, 255, 0)
RED = (255, 0, 0)


class Background(pygame.sprite.Sprite):
    def __init__(self, image_file):
        pygame.sprite.Sprite.__init__(self)  # call Sprite initializer
        self.image = pygame.image.load(image_file)
        self.rect = self.image.get_rect()
        # put in center
        w, h = pygame.display.get_surface().get_size()
        x = (w - self.rect.w) / 2
        y = (h - self.rect.h) / 2
        self.rect.left, self.rect.top = (x,y)


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
            self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((845, 480))
        self.bg = Background("bg.png")
        self.clock = pygame.time.Clock()
        self._quit = False

        self._display_active = False
        self._activation_time = 0
        self._time_active = 0
        self.color = BACKGROUND

    def scan_event(self, color):
        self.color = color
        self._display_active = True
        self.screen_update()
        self._activation_time = pygame.time.get_ticks()

    @flask_resource
    def scan_success(self):
        self.scan_event(GREEN)
        return "Scan success"

    @flask_resource
    def scan_failure(self):
        self.scan_event(RED)
        return "Scan failure"
    
    @flask_resource
    def default(self):
        return "hallo"

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

        for _ in range(0,2):
            self.screen_update()
            BACKGROUND = self.screen.get_at(self.bg.rect.midleft)[:-1]
            self.color = BACKGROUND

        while not self._quit:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit = True

            if self._display_active:
                self._time_active = pygame.time.get_ticks() - self._activation_time

            self.clock.tick(60)
            pygame.display.flip()

            if self._time_active >= 1000:
                self.color = BACKGROUND
                self._display_active = False
                self._time_active = 0
                self.screen_update()

        self.exit()

    def start(self):
        self.add_all_rules()
        kwargs = {
            'use_reloader': False
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
