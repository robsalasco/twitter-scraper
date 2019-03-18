import re
from requests_html import HTMLSession, HTML
from datetime import datetime

session = HTMLSession()


def get_tweets(user, pages=25):
    """Gets tweets for a given user, via the Twitter frontend API."""

    url = 'https://twitter.com/i/search/timeline?f=tweets&q=%20from%3A{}&src=typd&max_position={}'
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': f'https://twitter.com/{user}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
        'X-Twitter-Active-User': 'yes',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Language': 'en-US'
    }

    def gen_tweets(pages):
        position = ' '
        r = session.get(url.format(user, position), headers=headers)
        
        while pages > 0:
            if r.json()['has_more_items'] == True:
                try:
                    html = HTML(html=r.json()['items_html'],
                            url='bunk', default_encoding='utf-8')
                except KeyError:
                    raise ValueError(
                        f'Oops! Either "{user}" does not exist or is private.')
            else:
                print("No more items!")
                break

            comma = ","
            dot = "."
            tweets = []
            for tweet in html.find('.stream-item'):
                # 10~11 html elements have `.stream-item` class and also their `data-item-type` is `tweet`
                # but their content doesn't look like a tweet's content
                try:
                    text = tweet.find('.tweet-text')[0].full_text
                except IndexError:  # issue #50
                    continue

                tweet_id = tweet.find('.js-permalink')[0].attrs['data-conversation-id']

                time = datetime.fromtimestamp(int(tweet.find('._timestamp')[0].attrs['data-time-ms']) / 1000.0)

                interactions = [
                    x.text
                    for x in tweet.find('.ProfileTweet-actionCount')
                ]

                replies = int(
                    interactions[0].split(' ')[0].replace(comma, '').replace(dot, '')
                    or interactions[3]
                )

                retweets = int(
                    interactions[1].split(' ')[0].replace(comma, '').replace(dot, '')
                    or interactions[4]
                    or interactions[5]
                )

                likes = int(
                    interactions[2].split(' ')[0].replace(comma, '').replace(dot, '')
                    or interactions[6]
                    or interactions[7]
                )

                hashtags = [
                    hashtag_node.full_text
                    for hashtag_node in tweet.find('.twitter-hashtag')
                ]
                urls = [
                    url_node.attrs['data-expanded-url']
                    for url_node in tweet.find('a.twitter-timeline-link:not(.u-hidden)')
                ]
                photos = [
                    photo_node.attrs['data-image-url']
                    for photo_node in tweet.find('.AdaptiveMedia-photoContainer')
                ]

                videos = []
                video_nodes = tweet.find(".PlayableMedia-player")
                for node in video_nodes:
                    styles = node.attrs['style'].split()
                    for style in styles:
                        if style.startswith('background'):
                            tmp = style.split('/')[-1]
                            video_id = tmp[:tmp.index('.jpg')]
                            videos.append({'id': video_id})

                tweets.append({
                    'tweetId': tweet_id,
                    'time': time,
                    'text': text,
                    'replies': replies,
                    'retweets': retweets,
                    'likes': likes,
                    'entries': {
                        'hashtags': hashtags, 'urls': urls,
                        'photos': photos, 'videos': videos
                    }
                })

            position = str(r.json()['min_position'])
            next_url = url.format(user, position)

            for tweet in tweets:
                if tweet:
                    tweet['text'] = re.sub('http', ' http', tweet['text'], 1)
                    yield tweet

            r = session.get(
                next_url, headers = headers)
            
            pages += -1

    yield from gen_tweets(pages)
