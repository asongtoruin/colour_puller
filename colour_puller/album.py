class SpotifyAlbum:
    def __init__(self, resp_dict):
        self.name = resp_dict.get('name', None)
        self.release_date = resp_dict.get('release_date', 'Unknown')

        # Handle possibility of many artists
        artists = resp_dict['artists']
        if len(artists) > 5:
            self.artists = 'Various'
        else:
            self.artists = ', '.join(
                art.get('name', 'Unknown') for art in artists
            )
        
        urls = resp_dict.get('external_urls', {'spotify': None})
        self.link = urls['spotify']
        
        # Get the largest version of the album artwork
        images = resp_dict.get('images', [{'url': None, 'height': 0}])
        images.sort(key=lambda x: x['height'], reverse=True)
        self.art_link = images[0]['url']
    
    def __str__(self):
        return (
            f'Album Name: {self.name}\n'
            f'Artist(s): {self.artists}\n'
            f'Released: {self.release_date}\n'
            f'Link: {self.link}'
        )
    
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return NotImplemented
    
    def to_dict(self):
        return self.__dict__