import sqlite3

from .album import SpotifyAlbum


class AlbumDatabase:
    def __init__(self, db_path='spotify albums.sqlite'):
        self.conn = sqlite3.connect(db_path)
        # Get responses as dictionary
        self.conn.row_factory = sqlite3.Row

        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id text NOT NULL,
                name text NOT NULL,
                artists text NOT NULL,
                release_date text NOT NULL,
                link text,
                art_link text NOT NULL,
                status text DEFAULT "queued"
            )
            '''
        )

        self.conn.commit()

    def contains_album(self, album: SpotifyAlbum):
        self.cursor.execute('''
            SELECT * FROM albums 
            WHERE
                id = ?
            LIMIT 1
            ''',
            (album.id, )
        )

        resp = self.cursor.fetchone()

        return resp and len(resp) > 0

    def add_albums(self, albums):
        filter_new = [
            album for album in albums if not self.contains_album(album)
        ]

        self.cursor.executemany('''
            INSERT INTO albums (
                id, name, artists, release_date, link, art_link
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            [
                (
                    album.id, album.name, album.artists, album.release_date,
                    album.link, album.art_link
                )
                for album in filter_new
            ]
        )

        self.conn.commit()

    def update_album(self, album: SpotifyAlbum, status='processing'):
        if not status in ('queued', 'processing', 'completed', 'error'):
            raise ValueError(
                'status should be one of "queued", "processing", "completed" '
                f'or "error", received {status}'
            )
        
        self.cursor.execute('''
            UPDATE albums
            SET status=?
            WHERE
                id = ?
            ''',
            (status, album.id)
        )

        self.conn.commit()
    
    def get_from_queue(self):
        self.cursor.execute('''
            SELECT * FROM albums
            WHERE
                status="queued"
            LIMIT 1
            '''
        )

        resp = self.cursor.fetchone()
        if resp is not None:
            # convert from Row to dict
            resp_dict = dict(resp)

            # return Album object
            return SpotifyAlbum(resp_dict, from_api=False)
        else:
            return None
