from pathlib import Path
from flox import Flox, utils

from youtube_search import YoutubeSearch

BASE_URL = 'https://www.youtube.com'
DEFAULT_THUMB = 'default'
HIGH_QUALITY_THUMB = 'hq720'
THUMB_EXT = 'jpg'
MAX_THREADS = 10
DEFAULT_SEARCH_LIMIT = 10
TEN_MINUTES = 600
MAX_CACHE_AGE = TEN_MINUTES

class YouFlowTube(Flox):

    def _query(self, query):
        if query != '':
            path = Path(utils.gettempdir(), self.name)
            self._results = utils.cache(query, max_age=MAX_CACHE_AGE, dir=path)(self.query)(query)
        return self._results

    def query(self, query):
        limit = self.settings.get('max_search_results', DEFAULT_SEARCH_LIMIT)
        results = YoutubeSearch(query, max_results=limit).to_dict()
        for item in results:
            with utils.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                subtitle = f'{item["publish_time"]} - {item["channel"]} (Length: {item["duration"]})'
                thumbnail = item["thumbnails"][-1].replace(HIGH_QUALITY_THUMB, DEFAULT_THUMB)
                file_name = f'{item["id"]}.{THUMB_EXT}'
                url = f'{BASE_URL}{item["url_suffix"]}'
                icon = self.icon
                if self.settings.get('download_tumbs', True):
                    icon = utils.get_icon(thumbnail, self.name, file_name=file_name, executor=executor)
                self.add_item(
                    title=item['title'],
                    subtitle=subtitle,
                    icon=icon,
                    method=self.browser_open,
                    parameters=[url]
                )
        return self._results

    def context_menu(self, data):
        pass

if __name__ == "__main__":
    YouFlowTube()
