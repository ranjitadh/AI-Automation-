import random
import time
from typing import Optional

class AntiDetectionManager:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
        ]
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1440, "height": 900},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
        ]
        self.locales = ['en-US', 'en-GB', 'en-CA', 'en-AU']

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def get_random_viewport(self) -> dict:
        return random.choice(self.viewports)

    def get_random_locale(self) -> str:
        return random.choice(self.locales)

    @staticmethod
    def human_delay(min_ms=500, max_ms=2000):
        delay = random.randint(min_ms, max_ms) / 1000
        time.sleep(delay)

    @staticmethod
    def random_mouse_movement(page):
        try:
            vp = page.viewport_size
            if vp:
                x = random.randint(0, vp['width'])
                y = random.randint(0, vp['height'])
                page.mouse.move(x, y)
        except Exception:
            pass

    @staticmethod
    def random_scroll(page):
        try:
            for _ in range(random.randint(1, 3)):
                scroll_y = random.randint(100, 500)
                page.mouse.wheel(0, scroll_y)
                time.sleep(random.uniform(0.3, 1.0))
        except Exception:
            pass

    @staticmethod
    def spoof_webgl_fingerprint(page):
        try:
            page.add_init_script("""
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter(parameter);
                };
                const getExtension = WebGLRenderingContext.prototype.getExtension;
                WebGLRenderingContext.prototype.getExtension = function(name) {
                    if (name === 'WEBGL_debug_renderer_info') return null;
                    return getExtension.call(this, name);
                };
                Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
                    get: () => HTMLCanvasElement.prototype.toDataURL
                });
                const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    const canvas = this;
                    if (canvas.width === 0 && canvas.height === 0) return origToDataURL.call(canvas, type);
                    const noise = 0.0001;
                    const ctx = canvas.getContext('2d');
                    if (ctx) {
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + (Math.random() * noise - noise / 2)));
                            imageData.data[i+1] = Math.min(255, Math.max(0, imageData.data[i+1] + (Math.random() * noise - noise / 2)));
                            imageData.data[i+2] = Math.min(255, Math.max(0, imageData.data[i+2] + (Math.random() * noise - noise / 2)));
                        }
                        ctx.putImageData(imageData, 0, 0);
                    }
                    return origToDataURL.call(canvas, type);
                };
            """)
        except Exception:
            pass

    def get_browser_context_args(self):
        return {
            'user_agent': self.get_random_user_agent(),
            'viewport': self.get_random_viewport(),
            'locale': self.get_random_locale(),
            'timezone_id': 'America/New_York',
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
            'permissions': ['geolocation'],
        }
