import time
import random
import string
from locust import HttpUser, task, between


def random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


class URLShortenerUser(HttpUser):
    wait_time = between(1, 5)

    short_codes = []
    auth_token = None

    def on_start(self):
        email = f"test_{random_string(8)}@example.com"
        password = "Test@123456"

        self.client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password
            }
        )

        response = self.client.post(
            "/auth/jwt/login",
            data={
                "username": email,
                "password": password
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}

    @task(5)
    def create_short_link(self):
        original_url = f"https://example.com/{random_string(15)}"

        response = self.client.post(
            "/links/shorten",
            json={"original_url": original_url},
            headers=self.auth_headers if self.auth_token else None
        )

        if response.status_code == 200:
            data = response.json()
            short_code = data.get("short_code")
            if short_code:
                self.short_codes.append(short_code)

                if len(self.short_codes) > 50:
                    self.short_codes = self.short_codes[-50:]

    @task(10)
    def redirect_to_original(self):
        if not self.short_codes:
            self.create_short_link()
            return

        short_code = random.choice(self.short_codes)

        start_time = time.time()
        response = self.client.get(
            f"/links/{short_code}",
            allow_redirects=False,
            name="/links/[short_code]"
        )
        request_time = time.time() - start_time

        if response.status_code == 307:
            self.environment.events.request.fire(
                request_type="GET",
                name="Redirect Time",
                response_time=request_time * 1000,
                response_length=len(response.content),
                exception=None,
                context={}
            )

    @task(3)
    def get_link_stats(self):
        if not self.short_codes or not self.auth_token:
            return

        short_code = random.choice(self.short_codes)

        start_time = time.time()
        response = self.client.get(
            f"/links/{short_code}/stats",
            headers=self.auth_headers,
            name="/links/[short_code]/stats"
        )
        request_time = time.time() - start_time

        if response.headers.get("X-Cache") == "HIT":
            self.environment.events.request.fire(
                request_type="GET",
                name="Stats Cache Hit",
                response_time=request_time * 1000,
                response_length=len(response.content),
                exception=None,
                context={}
            )
        else:
            self.environment.events.request.fire(
                request_type="GET",
                name="Stats Cache Miss",
                response_time=request_time * 1000,
                response_length=len(response.content),
                exception=None,
                context={}
            )

    @task(1)
    def create_with_custom_alias(self):
        if not self.auth_token:
            return

        original_url = f"https://example.com/{random_string(15)}"
        custom_alias = random_string(8)

        response = self.client.post(
            "/links/shorten",
            json={
                "original_url": original_url,
                "custom_alias": custom_alias
            },
            headers=self.auth_headers,
            name="/links/shorten (custom)"
        )

        if response.status_code == 200:
            data = response.json()
            short_code = data.get("short_code")
            if short_code:
                self.short_codes.append(short_code)

    @task(1)
    def update_link(self):
        if not self.short_codes or not self.auth_token:
            return

        short_code = random.choice(self.short_codes)

        new_url = f"https://example.com/updated/{random_string(15)}"

        self.client.put(
            f"/links/{short_code}",
            json={"original_url": new_url},
            headers=self.auth_headers,
            name="/links/[short_code] (update)"
        )

    @task(1)
    def search_links(self):
        if not self.auth_token:
            return

        search_url = f"https://example.com/search/{random_string(8)}"

        response = self.client.post(
            "/links/shorten",
            json={"original_url": search_url},
            headers=self.auth_headers
        )

        if response.status_code == 200:
            start_time = time.time()
            response = self.client.get(
                f"/links/search/?original_url={search_url}",
                headers=self.auth_headers,
                name="/links/search/"
            )
            request_time = time.time() - start_time

            self.environment.events.request.fire(
                request_type="GET",
                name="Search Performance",
                response_time=request_time * 1000,
                response_length=len(response.content),
                exception=None,
                context={}
            )


class AnonymousUser(HttpUser):
    wait_time = between(1, 3)

    short_codes = []

    @task(3)
    def create_short_link_anonymous(self):
        original_url = f"https://example.com/anon/{random_string(15)}"

        response = self.client.post(
            "/links/shorten",
            json={"original_url": original_url}
        )

        if response.status_code == 200:
            data = response.json()
            short_code = data.get("short_code")
            if short_code:
                self.short_codes.append(short_code)

                if len(self.short_codes) > 20:
                    self.short_codes = self.short_codes[-20:]

    @task(7)
    def use_short_link_anonymous(self):
        if not self.short_codes:
            self.create_short_link_anonymous()
            return

        short_code = random.choice(self.short_codes)

        self.client.get(
            f"/links/{short_code}",
            allow_redirects=False,
            name="/links/[short_code] (anon)"
        )