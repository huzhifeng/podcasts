"""Podcasts"""
import os
from pathlib import Path
import json
import logging
import urllib
import time
import feedparser

def update_channel(item):
    """Update Channel"""
    fname_channel = f'channels/{item["channel"]}.md'
    md_old = ''

    Path('channels').mkdir(parents=True, exist_ok=True)
    if os.path.isfile(fname_channel):
        with open(fname_channel, mode='r', encoding='utf-8') as fd_channel_old:
            md_old = fd_channel_old.read()
            if md_old.find(item['link']) != -1:
                return

    md_new_entry = f'- [{item["title"]}]({item["link"]}) | [音频]({item["audio"]})\n'
    with open(fname_channel, mode='w', encoding='utf-8') as fd_channel_new:
        fd_channel_new.write(f'{md_new_entry}{md_old}')

def update_readme(item):
    """Update Readme"""
    fname_readme = 'README.md'
    md_old = ''
    md_new = ''

    md_new_entry = f'- {item["published"]} [{item["title"]}]({item["link"]}) \
| [音频]({item["audio"]}) \
| [More](channels/{urllib.parse.quote(item["channel"])}.md)'
    with open(fname_readme, mode='r', encoding='utf-8') as fd_readme_old:
        md_old = fd_readme_old.read()
        if md_old.find(item['link']) != -1:
            return
        i = md_old.find(f'## {item["channel"]}')
        if i != -1:
            j = md_old.find('-', i)
            k = md_old.rfind(')', i)
            if j != -1 and k != -1:
                md_old_entry = md_old[j:k + 1]
                md_new = md_old.replace(md_old_entry, md_new_entry)
        else:
            md_new = f'{md_old}## {item["channel"]}\n{md_new_entry}\n\n'

    with open(fname_readme, mode='w', encoding='utf-8') as fd_readme_new:
        fd_readme_new.write(f'{md_new}')

def cleanup_url(url):
    """Remove query string and AD tracking"""
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    if 'jt.ximalaya.com' in parsed_url.netloc and 'jt' in query_params:
        return query_params['jt'][0]

    clean_url = urllib.parse.urlunparse((parsed_url.scheme,
                                         parsed_url.netloc,
                                         parsed_url.path, '', '', ''))
    return clean_url

def main():
    """Main loop"""
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) '\
        'AppleWebKit/537.36 (KHTML, like Gecko) '\
        'Chrome/109.0.0.0 Safari/537.36'
    request_headers = {
        'user-agent': user_agent
    }
    feedparser.USER_AGENT = user_agent

    logger = logging.getLogger(__name__)
    logger.setLevel(os.environ.get('LOGLEVEL', 'INFO'))
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)

    conf = {}
    with open('feed.json', mode='r', encoding='utf-8') as fd_conf:
        conf = json.load(fd_conf)

    if 'feed' in conf:
        for feed in conf['feed']:
            if 'enable' in feed and feed['enable'] == 0:
                continue

            logger.debug(feed['url'])
            try:
                resp = feedparser.parse(feed['url'], request_headers=request_headers)
            except TimeoutError as e_timeout:
                logger.warning(e_timeout)
                continue
            except Exception as e_req:
                logger.warning(e_req)
                continue

            if not resp.has_key('entries'):
                logger.debug('no entries')
                continue

            # Order by ascending, most feed is descending by default
            if 'order' not in feed or 'descending' == feed['order']:
                resp.entries.reverse()

            i = 0
            total = len(resp.entries)
            for entry in resp.entries:
                item = {
                    'channel': feed['channel'],
                    'title': entry.title,
                    'link': cleanup_url(entry.link),
                    'audio': cleanup_url(entry.enclosures[0]['url']),
                    'published': time.strftime(
                        '%Y/%m/%d', entry.published_parsed if entry.has_key(
                        'published_parsed') else entry.updated_parsed)
                }
                logger.debug(item)
                update_channel(item)
                i = i + 1
                # Update the latest
                if i == total:
                    update_readme(item)

if __name__ == '__main__':
    main()
