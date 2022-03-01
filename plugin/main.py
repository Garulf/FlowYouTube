from pathlib import Path
from flox import Flox, utils, ICON_BROWSER

from youtube_search import YoutubeSearch

BASE_URL = 'https://www.youtube.com'
THUMBNAIL_URL = 'https://i.ytimg.com/vi'
DEFAULT_THUMB = 'default'
THUMB_EXT = 'jpg'
MAX_THREADS = 10
DEFAULT_SEARCH_LIMIT = 10
TEN_MINUTES = 600
MAX_CACHE_AGE = TEN_MINUTES

def get_thumbnail(id:str, thumb_type:str=DEFAULT_THUMB, ext:str=THUMB_EXT):
    """
    Get thumbnail url
    """
    return f'{THUMBNAIL_URL}/{id}/{thumb_type}.{THUMB_EXT}'

class FlowYouTube(Flox):

    def query(self, query):
        if query != '':
            path = Path(utils.gettempdir(), self.name)
            self._results = utils.cache(query, max_age=MAX_CACHE_AGE, dir=path)(self.search)(query)
        return self._results

    def search(self, query):
        limit = int(self.settings.get('max_search_results', DEFAULT_SEARCH_LIMIT))
        results = YoutubeSearch(query, max_results=limit).to_dict()
        for item in results:
            with utils.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                self.result(item, executor)
        return self._results

    def result(self, item, executor):
        icon = self.icon
        url = f'{BASE_URL}{item["url_suffix"]}'
        download_thumbs = self.settings.get('download_thumbs', True)
        if download_thumbs:
            icon = utils.get_icon(
                get_thumbnail(item['id']), 
                Path(self.name, 'thumbnails'), 
                file_name=f'{item["id"]}.{THUMB_EXT}', 
                executor=executor
            )
        self.add_item(
            title=item['title'],
            subtitle=f'{item["publish_time"]} - {item["channel"]} (Length: {item["duration"]})',
            icon=icon,
            method=self.browser_open,
            parameters=[url],
            context=[url]
        )

    def context_menu(self, data):
        url = data[0]
        self.add_item(
            title='Open in browser',
            icon=ICON_BROWSER,
            method=self.browser_open,
            parameters=[url]
        )

if __name__ == "__main__":
    FlowYouTube()
